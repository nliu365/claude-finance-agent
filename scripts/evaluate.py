#!/usr/bin/env python3
"""Enhanced evaluation harness for MD&A macro-factor sentiment tasks.

Usage:
  python3 scripts/evaluate.py --gt evaluation/labels.jsonl --pred outputs.jsonl
  python3 scripts/evaluate.py --gt evaluation/labels.jsonl --pred outputs.jsonl --detailed
  python3 scripts/evaluate.py --gt evaluation/labels.jsonl --pred outputs.jsonl --tolerance 0.15

Both files should be JSONL where each line is a JSON object. Ground-truth lines must follow
the schema in evaluation/label_schema.json.

Predictions should be objects containing at least:
- id (matching gt id)
- factor
- sentiment_score
- support_sentences (list)

Features:
- Separate identification accuracy and sentiment accuracy scoring
- Tolerance bands for near-miss scoring (addressing gaps between sentiment levels)
- Mixed sentiment handling with sub-statement analysis
- Label-level matching in addition to numeric score matching
- Detailed per-item breakdown with --detailed flag

Based on the Alpha Cortex Green Agent Task Brainstorming requirements.
"""
import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from scripts.scoring_rubric import (
    SentimentLabel,
    score_to_label,
    sentiment_match_with_tolerance,
    label_match_score,
    detect_mixed_sentiment_indicators,
    DEFAULT_TOLERANCE,
)


def normalize_text(s: str) -> str:
    return " ".join(s.lower().strip().split())


def jaccard(a: List[str], b: List[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa and not sb:
        return 1.0
    inter = sa.intersection(sb)
    uni = sa.union(sb)
    return len(inter) / len(uni)


def clause_split(sentence: str) -> List[str]:
    import re

    s = sentence.strip()
    # split on commas, semicolons, or the word ' and ' (simple heuristic)
    parts = re.split(r"[,;]|\band\b", s)
    parts = [normalize_text(p) for p in parts if p.strip()]
    return parts or [normalize_text(s)]


def sentence_match_score(gt_sentence: str, candidate_sentences: List[str]) -> float:
    """Return a match score in [0,1] between gt_sentence and candidate_sentences.

    Uses clause-level matching: splits GT into clauses and computes average max-jaccard
    between each clause and any of the candidate sentences.
    """
    gt_clauses = clause_split(gt_sentence)
    cand_norms = [normalize_text(c) for c in (candidate_sentences or [])]
    cand_tokens = [c.split() for c in cand_norms]
    scores = []
    for clause in gt_clauses:
        ctoks = clause.split()
        best = 0.0
        for c_toks in cand_tokens:
            score = jaccard(ctoks, c_toks)
            if score > best:
                best = score
        # also check substring containment as stronger match
        for c in cand_norms:
            if clause and (clause in c or c in clause):
                best = max(best, 1.0)
        scores.append(best)
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def sentiment_score_match(gt_score: float, pred_score: float) -> float:
    """Basic sentiment score match (legacy behavior).

    Normalized 0..1 where 1 is exact match, penalize by absolute difference over full range 2.
    """
    err = abs(gt_score - pred_score)
    return max(0.0, 1.0 - (err / 2.0))


def sentiment_score_match_enhanced(
    gt_score: float, pred_score: float, tolerance: float = DEFAULT_TOLERANCE
) -> Tuple[float, float, float]:
    """Enhanced sentiment score match with tolerance bands.

    Returns:
        Tuple of (basic_score, tolerance_score, label_score) where:
        - basic_score: Legacy linear scoring
        - tolerance_score: Score with tolerance bands for near-miss credit
        - label_score: Score based on label proximity (discrete categories)
    """
    basic_score = sentiment_score_match(gt_score, pred_score)
    tolerance_score = sentiment_match_with_tolerance(gt_score, pred_score, tolerance)

    gt_label = score_to_label(gt_score)
    pred_label = score_to_label(pred_score)
    label_score_val = label_match_score(gt_label, pred_label)

    return (basic_score, tolerance_score, label_score_val)


def analyze_mixed_sentiment(
    gt_record: Dict, pred_record: Dict
) -> Optional[Dict]:
    """Analyze if ground truth or prediction contains mixed sentiment.

    Returns analysis dict if mixed sentiment detected, None otherwise.
    """
    gt_sentence = gt_record.get("sentence", "")
    indicators = detect_mixed_sentiment_indicators(gt_sentence)

    if not indicators:
        return None

    # Check if GT has clauses annotation
    gt_clauses = gt_record.get("clauses", [])

    return {
        "is_mixed": True,
        "indicators": indicators,
        "gt_clauses": gt_clauses,
        "gt_score": gt_record.get("sentiment_score", 0.0),
        "pred_score": pred_record.get("sentiment_score") if pred_record else None,
    }


def evaluate(
    gt_records: List[Dict],
    pred_records: List[Dict],
    tolerance: float = DEFAULT_TOLERANCE,
    detailed: bool = False,
) -> Dict:
    """Evaluate predictions against ground truth with enhanced metrics.

    Args:
        gt_records: List of ground truth records
        pred_records: List of prediction records
        tolerance: Tolerance band for near-miss scoring (default 0.1)
        detailed: If True, include per-item breakdown in results

    Returns:
        Dictionary with evaluation metrics including:
        - items: Total number of items evaluated
        - identification: Average identification accuracy
        - sentiment_basic: Basic sentiment match score
        - sentiment_tolerance: Sentiment match with tolerance bands
        - sentiment_label: Label-level match score
        - sentiment: Combined sentiment score (weighted average)
        - composite: Overall composite score (40% identification + 60% sentiment)
        - mixed_sentiment_analysis: Analysis of mixed sentiment items
        - per_item: (if detailed) Per-item breakdown
    """
    pred_by_id = {p.get("id"): p for p in pred_records}

    # Score accumulators
    id_scores = []
    sent_basic_scores = []
    sent_tolerance_scores = []
    sent_label_scores = []

    # Per-item details
    per_item_details = []

    # Mixed sentiment tracking
    mixed_items = []

    items = 0
    for gt in gt_records:
        gid = gt["id"]
        items += 1
        pred = pred_by_id.get(gid)

        item_detail = {
            "id": gid,
            "factor": gt.get("factor", "unknown"),
            "gt_score": gt.get("sentiment_score"),
            "gt_label": gt.get("sentiment_label"),
            "gt_sentence": gt.get("sentence", "")[:100] + "..." if len(gt.get("sentence", "")) > 100 else gt.get("sentence", ""),
        }

        if not pred:
            id_scores.append(0.0)
            sent_basic_scores.append(0.0)
            sent_tolerance_scores.append(0.0)
            sent_label_scores.append(0.0)
            item_detail.update({
                "pred_score": None,
                "identification_score": 0.0,
                "sentiment_basic": 0.0,
                "sentiment_tolerance": 0.0,
                "sentiment_label": 0.0,
                "missing_prediction": True,
            })
            per_item_details.append(item_detail)
            continue

        # Identification score
        cand = pred.get("support_sentences", []) or pred.get("sentences", [])
        match_score = sentence_match_score(gt["sentence"], cand)
        id_scores.append(match_score)

        # Sentiment scores
        ps = pred.get("sentiment_score")
        if ps is None:
            sent_basic_scores.append(0.0)
            sent_tolerance_scores.append(0.0)
            sent_label_scores.append(0.0)
            item_detail.update({
                "pred_score": None,
                "identification_score": match_score,
                "sentiment_basic": 0.0,
                "sentiment_tolerance": 0.0,
                "sentiment_label": 0.0,
            })
        else:
            gt_score = float(gt["sentiment_score"])
            pred_score = float(ps)
            basic, tol, label = sentiment_score_match_enhanced(gt_score, pred_score, tolerance)
            sent_basic_scores.append(basic)
            sent_tolerance_scores.append(tol)
            sent_label_scores.append(label)

            item_detail.update({
                "pred_score": pred_score,
                "identification_score": match_score,
                "sentiment_basic": basic,
                "sentiment_tolerance": tol,
                "sentiment_label": label,
                "score_error": abs(gt_score - pred_score),
            })

        # Check for mixed sentiment
        mixed_analysis = analyze_mixed_sentiment(gt, pred)
        if mixed_analysis:
            mixed_items.append({
                "id": gid,
                **mixed_analysis,
            })
            item_detail["has_mixed_sentiment"] = True

        per_item_details.append(item_detail)

    # Compute averages
    identification = sum(id_scores) / items if items else 0.0
    sentiment_basic = sum(sent_basic_scores) / items if items else 0.0
    sentiment_tolerance = sum(sent_tolerance_scores) / items if items else 0.0
    sentiment_label = sum(sent_label_scores) / items if items else 0.0

    # Combined sentiment score (weighted average of different metrics)
    # 50% tolerance-based, 30% basic, 20% label-based
    sentiment = 0.5 * sentiment_tolerance + 0.3 * sentiment_basic + 0.2 * sentiment_label

    # Composite score (40% identification + 60% sentiment)
    composite = 0.4 * identification + 0.6 * sentiment

    result = {
        "items": items,
        "identification": round(identification, 4),
        "sentiment_basic": round(sentiment_basic, 4),
        "sentiment_tolerance": round(sentiment_tolerance, 4),
        "sentiment_label": round(sentiment_label, 4),
        "sentiment": round(sentiment, 4),
        "composite": round(composite, 4),
        "tolerance_used": tolerance,
        "mixed_sentiment_count": len(mixed_items),
    }

    if mixed_items:
        result["mixed_sentiment_analysis"] = {
            "count": len(mixed_items),
            "items": mixed_items[:5],  # Limit to 5 examples
        }

    if detailed:
        result["per_item"] = per_item_details

    return result


def evaluate_by_factor(
    gt_records: List[Dict],
    pred_records: List[Dict],
    tolerance: float = DEFAULT_TOLERANCE,
) -> Dict:
    """Evaluate predictions grouped by factor.

    Returns per-factor metrics in addition to overall metrics.
    """
    # Group by factor
    factors = set(gt.get("factor", "unknown") for gt in gt_records)

    factor_results = {}
    for factor in sorted(factors):
        factor_gt = [gt for gt in gt_records if gt.get("factor") == factor]
        factor_pred = [
            p for p in pred_records
            if p.get("id") in {gt["id"] for gt in factor_gt}
        ]
        factor_results[factor] = evaluate(factor_gt, factor_pred, tolerance, detailed=False)

    # Overall results
    overall = evaluate(gt_records, pred_records, tolerance, detailed=False)

    return {
        "overall": overall,
        "by_factor": factor_results,
    }


def read_jsonl(path: Path) -> List[Dict]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            out.append(json.loads(ln))
    return out


def main():
    p = argparse.ArgumentParser(
        description="Evaluate MD&A sentiment predictions against ground truth.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic evaluation
  python3 scripts/evaluate.py --gt evaluation/sample_labels.jsonl --pred evaluation/sample_predictions.jsonl

  # Detailed per-item breakdown
  python3 scripts/evaluate.py --gt evaluation/sample_labels.jsonl --pred evaluation/sample_predictions.jsonl --detailed

  # Custom tolerance band
  python3 scripts/evaluate.py --gt evaluation/sample_labels.jsonl --pred evaluation/sample_predictions.jsonl --tolerance 0.15

  # Per-factor breakdown
  python3 scripts/evaluate.py --gt evaluation/sample_labels.jsonl --pred evaluation/sample_predictions.jsonl --by-factor
        """,
    )
    p.add_argument("--gt", required=True, help="Ground-truth JSONL file")
    p.add_argument("--pred", required=True, help="Predictions JSONL file")
    p.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=f"Tolerance band for near-miss scoring (default: {DEFAULT_TOLERANCE})",
    )
    p.add_argument(
        "--detailed",
        action="store_true",
        help="Include per-item breakdown in results",
    )
    p.add_argument(
        "--by-factor",
        action="store_true",
        help="Show per-factor breakdown in addition to overall metrics",
    )
    p.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file for results (default: stdout)",
    )

    args = p.parse_args()
    gt_path = Path(args.gt)
    pred_path = Path(args.pred)

    if not gt_path.exists():
        print(f"Error: Ground truth file not found: {gt_path}", file=__import__("sys").stderr)
        __import__("sys").exit(1)
    if not pred_path.exists():
        print(f"Error: Predictions file not found: {pred_path}", file=__import__("sys").stderr)
        __import__("sys").exit(1)

    gt = read_jsonl(gt_path)
    pred = read_jsonl(pred_path)

    if args.by_factor:
        result = evaluate_by_factor(gt, pred, args.tolerance)
    else:
        result = evaluate(gt, pred, args.tolerance, args.detailed)

    output = json.dumps(result, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Results written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
