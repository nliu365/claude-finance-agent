#!/usr/bin/env python3
"""Scoring rubric definitions and utilities for MD&A sentiment analysis.

This module defines the sentiment scoring rubric used for ground-truth labeling
and evaluation. It addresses:
1. Detailed sentiment ranges from -1.0 to +1.0
2. Tolerance bands for near-miss scoring (addressing gaps between levels)
3. Mixed sentiment handling
4. Separate identification vs sentiment accuracy

Based on the Alpha Cortex Green Agent Task Brainstorming document.
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class SentimentLabel(Enum):
    """Sentiment labels with associated score ranges."""

    STRONGLY_NEGATIVE = "strongly_negative"
    NEGATIVE = "negative"
    SLIGHTLY_NEGATIVE = "slightly_negative"
    NEUTRAL = "neutral"
    SLIGHTLY_POSITIVE = "slightly_positive"
    POSITIVE = "positive"
    STRONGLY_POSITIVE = "strongly_positive"


class ConfidenceLevel(Enum):
    """Confidence level for competition analysis (Ning's idea #1)."""

    OPTIMISTIC = "optimistic"
    NEUTRAL = "neutral"
    PESSIMISTIC = "pessimistic"


class PerformanceLevel(Enum):
    """Performance level for outlook analysis (Ning's idea #2)."""

    OVER_PERFORMANCE = "over_performance"
    NEUTRAL = "neutral"
    UNDER_PERFORMANCE = "under_performance"


@dataclass
class SentimentRange:
    """Defines a sentiment range with min/max scores and keywords."""

    label: SentimentLabel
    min_score: float
    max_score: float
    keywords: List[str]
    description: str

    def contains(self, score: float) -> bool:
        """Check if a score falls within this range."""
        return self.min_score <= score <= self.max_score

    def center(self) -> float:
        """Return the center of this range."""
        return (self.min_score + self.max_score) / 2


# Define the sentiment rubric with closed intervals (no gaps)
# The ranges now overlap slightly at boundaries for tolerance
SENTIMENT_RUBRIC: List[SentimentRange] = [
    SentimentRange(
        label=SentimentLabel.STRONGLY_NEGATIVE,
        min_score=-1.0,
        max_score=-0.75,
        keywords=[
            "materially adverse",
            "significant downturn",
            "severe risk",
            "critical threat",
            "substantial loss",
            "significant decline",
        ],
        description="Explicit severe negative outlook with significant business impact.",
    ),
    SentimentRange(
        label=SentimentLabel.NEGATIVE,
        min_score=-0.75,
        max_score=-0.35,
        keywords=[
            "headwind",
            "unfavorable",
            "negatively impacted",
            "pressure",
            "challenging",
            "decline",
            "decreased",
            "reduced",
        ],
        description="Clearly negative outlook but not catastrophic.",
    ),
    SentimentRange(
        label=SentimentLabel.SLIGHTLY_NEGATIVE,
        min_score=-0.35,
        max_score=-0.05,
        keywords=[
            "modest headwind",
            "minor pressure",
            "manageable",
            "slight decrease",
            "limited impact",
            "somewhat unfavorable",
        ],
        description="Minimal negative impact acknowledged.",
    ),
    SentimentRange(
        label=SentimentLabel.NEUTRAL,
        min_score=-0.05,
        max_score=0.05,
        keywords=[
            "remained stable",
            "unchanged",
            "immaterial effect",
            "minimal impact",
            "flat",
            "consistent",
        ],
        description="Purely factual statement with no emotional language.",
    ),
    SentimentRange(
        label=SentimentLabel.SLIGHTLY_POSITIVE,
        min_score=0.05,
        max_score=0.35,
        keywords=[
            "modest improvement",
            "limited upside",
            "slight increase",
            "somewhat favorable",
            "marginally better",
        ],
        description="Acknowledges positive factor but minimal impact.",
    ),
    SentimentRange(
        label=SentimentLabel.POSITIVE,
        min_score=0.35,
        max_score=0.75,
        keywords=[
            "expect to benefit",
            "could improve",
            "positive trend",
            "confident",
            "favorable",
            "growth",
            "increased",
            "improved",
        ],
        description="Generally positive outlook with some certainty.",
    ),
    SentimentRange(
        label=SentimentLabel.STRONGLY_POSITIVE,
        min_score=0.75,
        max_score=1.0,
        keywords=[
            "significant opportunity",
            "strong benefit",
            "favorable",
            "exceeded expectations",
            "substantial growth",
            "excellent",
            "outstanding",
        ],
        description="Explicit positive outlook with strong confidence.",
    ),
]


def score_to_label(score: float) -> SentimentLabel:
    """Convert a numeric sentiment score to a sentiment label.

    Uses the defined rubric ranges. For boundary cases, uses the
    closest range center to determine the label.
    """
    score = max(-1.0, min(1.0, score))  # Clamp to valid range

    for sr in SENTIMENT_RUBRIC:
        if sr.contains(score):
            return sr.label

    # Fallback: find closest range center
    closest = min(SENTIMENT_RUBRIC, key=lambda r: abs(r.center() - score))
    return closest.label


def label_to_score_range(label: SentimentLabel) -> Tuple[float, float]:
    """Get the score range for a given sentiment label."""
    for sr in SENTIMENT_RUBRIC:
        if sr.label == label:
            return (sr.min_score, sr.max_score)
    return (-1.0, 1.0)  # Fallback


def get_label_keywords(label: SentimentLabel) -> List[str]:
    """Get the keywords associated with a sentiment label."""
    for sr in SENTIMENT_RUBRIC:
        if sr.label == label:
            return sr.keywords
    return []


# Tolerance bands for near-miss scoring (Ning's concern about gaps)
DEFAULT_TOLERANCE = 0.1  # ±0.1 tolerance for partial credit


def sentiment_match_with_tolerance(
    gt_score: float, pred_score: float, tolerance: float = DEFAULT_TOLERANCE
) -> float:
    """Compute sentiment match score with tolerance bands.

    Returns:
        Float in [0, 1] where:
        - 1.0 = exact match (within tolerance)
        - 0.5-1.0 = partial match (within 2x tolerance)
        - 0.0-0.5 = poor match (outside tolerance)

    This addresses the gap issue between neighboring levels by giving
    partial credit for near-miss predictions.
    """
    error = abs(gt_score - pred_score)

    if error <= tolerance:
        # Full credit for predictions within tolerance
        return 1.0
    elif error <= 2 * tolerance:
        # Partial credit: linearly decrease from 1.0 to 0.5
        return 1.0 - 0.5 * ((error - tolerance) / tolerance)
    else:
        # Decreasing credit based on error over full range
        # Normalize by 2.0 (full range from -1 to +1)
        return max(0.0, 0.5 * (1.0 - (error - 2 * tolerance) / (2.0 - 2 * tolerance)))


def label_match_score(gt_label: SentimentLabel, pred_label: SentimentLabel) -> float:
    """Compute label match score based on label proximity.

    Returns:
        Float in [0, 1] where:
        - 1.0 = exact label match
        - 0.75 = adjacent label (1 level off)
        - 0.5 = 2 levels off
        - 0.0 = opposite ends
    """
    label_order = [
        SentimentLabel.STRONGLY_NEGATIVE,
        SentimentLabel.NEGATIVE,
        SentimentLabel.SLIGHTLY_NEGATIVE,
        SentimentLabel.NEUTRAL,
        SentimentLabel.SLIGHTLY_POSITIVE,
        SentimentLabel.POSITIVE,
        SentimentLabel.STRONGLY_POSITIVE,
    ]

    gt_idx = label_order.index(gt_label)
    pred_idx = label_order.index(pred_label)
    distance = abs(gt_idx - pred_idx)

    # Max distance is 6 (strongly_negative to strongly_positive)
    return max(0.0, 1.0 - (distance / 6.0) * 1.0)


@dataclass
class MixedSentimentResult:
    """Result of mixed sentiment analysis."""

    original_sentence: str
    sub_statements: List[dict]  # Each with text, sentiment_score, sentiment_label
    aggregated_score: float
    aggregation_method: str  # "mean" or "weighted_by_length"


def aggregate_mixed_sentiment(
    sub_scores: List[Tuple[str, float]], method: str = "weighted_by_length"
) -> float:
    """Aggregate sentiment scores from sub-statements.

    Args:
        sub_scores: List of (text, score) tuples for each sub-statement
        method: Aggregation method ("mean" or "weighted_by_length")

    Returns:
        Aggregated sentiment score
    """
    if not sub_scores:
        return 0.0

    if method == "mean":
        return sum(score for _, score in sub_scores) / len(sub_scores)
    elif method == "weighted_by_length":
        total_length = sum(len(text) for text, _ in sub_scores)
        if total_length == 0:
            return 0.0
        weighted_sum = sum(len(text) * score for text, score in sub_scores)
        return weighted_sum / total_length
    else:
        raise ValueError(f"Unknown aggregation method: {method}")


def detect_mixed_sentiment_indicators(text: str) -> List[str]:
    """Detect indicators of mixed sentiment in text.

    Returns list of detected indicator phrases.
    """
    indicators = []
    text_lower = text.lower()

    contrast_words = ["but", "however", "although", "despite", "while", "yet", "nevertheless"]
    for word in contrast_words:
        if f" {word} " in f" {text_lower} ":
            indicators.append(word)

    contrast_patterns = [
        ("increased", "offset"),
        ("growth", "decline"),
        ("benefited", "impacted"),
        ("improved", "decreased"),
        ("gain", "loss"),
    ]
    for pos, neg in contrast_patterns:
        if pos in text_lower and neg in text_lower:
            indicators.append(f"{pos}...{neg}")

    hedge_words = ["partially", "somewhat", "to some extent", "largely offset", "mostly offset"]
    for hedge in hedge_words:
        if hedge in text_lower:
            indicators.append(hedge)

    return indicators


def split_mixed_sentiment_sentence(sentence: str) -> List[str]:
    """Split a sentence with mixed sentiment into sub-statements.

    Uses clause boundaries (commas, semicolons, conjunctions) to split.
    """
    import re

    # Split on common clause boundaries
    parts = re.split(r"[,;]|\s+(?:but|however|although|despite|while|yet)\s+", sentence, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]

    # Further split on "and" if it connects contrasting elements
    final_parts = []
    for part in parts:
        if " and " in part.lower():
            sub_parts = re.split(r"\s+and\s+", part, flags=re.IGNORECASE)
            final_parts.extend([sp.strip() for sp in sub_parts if sp.strip()])
        else:
            final_parts.append(part)

    return final_parts if final_parts else [sentence]


# Competition confidence scoring (Ning's idea #1)
def confidence_score_to_level(score: float) -> ConfidenceLevel:
    """Convert confidence score to level for competition analysis."""
    if score >= 0.4:
        return ConfidenceLevel.OPTIMISTIC
    elif score <= -0.4:
        return ConfidenceLevel.PESSIMISTIC
    else:
        return ConfidenceLevel.NEUTRAL


def confidence_level_to_score_range(level: ConfidenceLevel) -> Tuple[float, float]:
    """Get score range for a confidence level."""
    if level == ConfidenceLevel.OPTIMISTIC:
        return (0.4, 1.0)
    elif level == ConfidenceLevel.PESSIMISTIC:
        return (-1.0, -0.4)
    else:
        return (-0.3, 0.3)


# Outlook performance scoring (Ning's idea #2)
def performance_score_to_level(score: float) -> PerformanceLevel:
    """Convert performance score to level for outlook analysis."""
    if score >= 0.4:
        return PerformanceLevel.OVER_PERFORMANCE
    elif score <= -0.4:
        return PerformanceLevel.UNDER_PERFORMANCE
    else:
        return PerformanceLevel.NEUTRAL


def performance_level_to_score_range(level: PerformanceLevel) -> Tuple[float, float]:
    """Get score range for a performance level."""
    if level == PerformanceLevel.OVER_PERFORMANCE:
        return (0.4, 1.0)
    elif level == PerformanceLevel.UNDER_PERFORMANCE:
        return (-1.0, -0.4)
    else:
        return (-0.3, 0.3)


# Export rubric as dict for JSON serialization
def rubric_to_dict() -> dict:
    """Export the sentiment rubric as a dictionary for documentation."""
    return {
        "sentiment_ranges": [
            {
                "label": sr.label.value,
                "min_score": sr.min_score,
                "max_score": sr.max_score,
                "keywords": sr.keywords,
                "description": sr.description,
            }
            for sr in SENTIMENT_RUBRIC
        ],
        "tolerance": DEFAULT_TOLERANCE,
        "confidence_levels": {
            "optimistic": {"range": [0.4, 1.0]},
            "neutral": {"range": [-0.3, 0.3]},
            "pessimistic": {"range": [-1.0, -0.4]},
        },
        "performance_levels": {
            "over_performance": {"range": [0.4, 1.0]},
            "neutral": {"range": [-0.3, 0.3]},
            "under_performance": {"range": [-1.0, -0.4]},
        },
    }


if __name__ == "__main__":
    import json

    print("Sentiment Scoring Rubric")
    print("=" * 60)
    print(json.dumps(rubric_to_dict(), indent=2))
