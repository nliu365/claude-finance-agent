#!/usr/bin/env python3
"""Generate prompt templates for MD&A macro-factor sentiment tasks.

Supports:
- Standard factor extraction (interest_rates, fx, inflation, etc.)
- Competition confidence analysis (Ning's idea)
- Outlook performance analysis (Ning's idea)
- Mixed sentiment handling
"""
import json
from pathlib import Path

# Standard macro factors for sentiment extraction
FACTORS = [
    "interest_rates",
    "fx",
    "inflation",
    "competition",
    "supply_chain",
    "regulation",
    "trade_policy",
]

# Extended task types (Ning's additions)
EXTENDED_TASKS = [
    "competition_confidence",
    "outlook_performance",
    "mixed_sentiment",
]

# Sentiment scoring rubric for reference in prompts
SENTIMENT_RUBRIC = """
SENTIMENT SCORING RUBRIC:
- +0.8 to +1.0 (strongly_positive): Explicit positive outlook. Keywords: "significant opportunity", "strong benefit", "favorable", "exceeded expectations".
- +0.4 to +0.7 (positive): Generally positive but less certain. Keywords: "expect to benefit", "could improve", "positive trend", "confident".
- +0.1 to +0.3 (slightly_positive): Acknowledges positive factor but minimal impact. Keywords: "modest improvement", "limited upside".
- 0.0 (neutral): Purely factual, no emotional language. Keywords: "remained stable", "unchanged", "immaterial effect".
- -0.1 to -0.3 (slightly_negative): Minimal negative impact. Keywords: "modest headwind", "minor pressure", "manageable".
- -0.4 to -0.7 (negative): Clear negative but not catastrophic. Keywords: "headwind", "unfavorable", "negatively impacted", "pressure", "challenging".
- -0.8 to -1.0 (strongly_negative): Explicit severe risk. Keywords: "materially adverse", "significant downturn", "severe risk", "critical threat".
"""

# Standard factor template
TEMPLATE = (
    "TASK: For the provided MD&A text, locate statements about {factor}.\n"
    "OUTPUT: JSON array of objects with fields: sentence, sentiment_score (-1.0..1.0), sentiment_label, justification, provenance (optional).\n"
    "INSTRUCTIONS: Return at most 5 items; pick the most representative sentences. If none found, return an empty array.\n"
    f"\n{SENTIMENT_RUBRIC}"
)

# Competition confidence template (Ning's idea #1)
COMPETITION_CONFIDENCE_TEMPLATE = """
TASK: Extract mentions of competition condition changes from the MD&A text.
For each mention, classify the company's confidence level to succeed against competition.

OUTPUT: JSON array of objects with the following fields:
- sentence: The extracted sentence mentioning competition
- confidence_level: One of "optimistic", "neutral", or "pessimistic"
- confidence_score: Float from -1.0 (very pessimistic) to +1.0 (very optimistic)
- competitive_factors: List of specific competitive factors mentioned (e.g., "market_share", "pricing_power", "innovation", "new_entrants")
- justification: Brief rationale for the classification
- provenance: Optional object with paragraph_index, char_start, char_end

CONFIDENCE SCORING RUBRIC:
- Optimistic (+0.4 to +1.0): Company expresses confidence in competitive position.
  Keywords: "confident", "well-positioned", "competitive advantage", "gain share", "differentiated", "leading position".
- Neutral (-0.3 to +0.3): Acknowledges competition without clear positive or negative outlook.
  Keywords: "competitive landscape", "market dynamics", "industry trends", "comparable to peers".
- Pessimistic (-1.0 to -0.4): Expresses concern about competitive threats.
  Keywords: "intensifying competition", "market share loss", "pricing pressure from competitors", "new entrants threatening".

INSTRUCTIONS:
- Return at most 5 items; prioritize the most representative sentences.
- Consider both explicit statements about competitors and implicit competitive positioning.
- If no competition mentions found, return an empty array.
"""

# Outlook performance template (Ning's idea #2)
OUTLOOK_PERFORMANCE_TEMPLATE = """
TASK: Analyze outlook statements and guidance in the MD&A text.
Compare current outlook/guidance with previous guidance or prior period performance to determine if the company is performing over/neutral/under expectations.

OUTPUT: JSON array of objects with the following fields:
- sentence: The extracted outlook or guidance statement
- performance_classification: One of "over_performance", "neutral", or "under_performance"
- performance_score: Float from -1.0 (significantly under) to +1.0 (significantly over)
- metrics_mentioned: List of specific metrics referenced (e.g., "revenue_growth", "margin", "eps", "market_share")
- comparison_basis: What the outlook is compared against (e.g., "prior_guidance", "last_year", "consensus", "industry_average")
- numeric_values: Optional object with extracted numbers (current_value, prior_value, change_percent)
- justification: Brief rationale for the classification
- provenance: Optional object with paragraph_index, char_start, char_end

PERFORMANCE SCORING RUBRIC:
- Over Performance (+0.4 to +1.0): Results/outlook exceed prior guidance or expectations.
  Keywords: "exceeded expectations", "above guidance", "beat", "outperformed", "raised outlook", "better than expected".
- Neutral (-0.3 to +0.3): Results/outlook in line with prior guidance.
  Keywords: "in line with", "consistent with guidance", "as expected", "on track", "reaffirmed".
- Under Performance (-1.0 to -0.4): Results/outlook below prior guidance or expectations.
  Keywords: "below expectations", "missed guidance", "lowered outlook", "underperformed", "revised down".

INSTRUCTIONS:
- Return at most 5 items; prioritize statements with explicit numeric comparisons.
- Look for year-over-year comparisons, guidance updates, and forward-looking statements.
- If no outlook/guidance statements found, return an empty array.
"""

# Mixed sentiment template
MIXED_SENTIMENT_TEMPLATE = """
TASK: Identify sentences with mixed sentiment (both positive and negative elements) in the MD&A text.
Split complex sentences into sub-statements where possible and score each component.

OUTPUT: JSON array of objects with the following fields:
- original_sentence: The full sentence containing mixed sentiment
- sub_statements: Array of objects, each with:
  - text: The sub-statement text
  - sentiment_score: Float from -1.0 to +1.0
  - sentiment_label: One of strongly_negative, negative, slightly_negative, neutral, slightly_positive, positive, strongly_positive
  - is_positive: Boolean indicating if this sub-statement is positive
- aggregated_score: Weighted average of sub-statement scores
- aggregation_method: "mean" or "weighted_by_length"
- justification: Explanation of how the aggregated score was derived
- provenance: Optional object with paragraph_index, char_start, char_end

MIXED SENTIMENT INDICATORS:
- Conjunctions: "but", "however", "although", "despite", "while", "on the other hand"
- Contrast patterns: "increased... offset by", "growth in... decline in", "benefited... impacted by"
- Hedge words: "partially", "somewhat", "to some extent", "largely offset"

INSTRUCTIONS:
- Focus on sentences that contain both positive and negative sentiment elements.
- Use clause boundaries (commas, semicolons, conjunctions) to split sub-statements.
- Weight sub-statements by importance or length when computing aggregated score.
- Return at most 5 items; prioritize the most clearly mixed sentences.
- If no mixed sentiment sentences found, return an empty array.
"""


def generate_prompts(out_dir: Path):
    """Generate all prompt templates for MD&A analysis tasks.

    Creates:
    - Individual factor prompts (interest_rates, fx, etc.)
    - Combined multi-factor prompt
    - Competition confidence prompt (Ning's idea)
    - Outlook performance prompt (Ning's idea)
    - Mixed sentiment prompt
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate standard factor prompts
    for f in FACTORS:
        content = TEMPLATE.format(factor=f)
        (out_dir / f"prompt_{f}.txt").write_text(content, encoding="utf-8")

    # Generate extended task prompts (Ning's additions)
    (out_dir / "prompt_competition_confidence.txt").write_text(
        COMPETITION_CONFIDENCE_TEMPLATE, encoding="utf-8"
    )
    (out_dir / "prompt_outlook_performance.txt").write_text(
        OUTLOOK_PERFORMANCE_TEMPLATE, encoding="utf-8"
    )
    (out_dir / "prompt_mixed_sentiment.txt").write_text(
        MIXED_SENTIMENT_TEMPLATE, encoding="utf-8"
    )

    # Generate combined multi-factor prompt with rubric
    combined = f"""TASK: For the provided MD&A text, analyze each macro factor and produce a comprehensive sentiment assessment.

FACTORS TO ANALYZE:
- interest_rates: Interest rate environment and impact on business
- fx: Foreign currency exchange rate effects
- inflation: Inflationary pressures and pricing power
- competition: Competitive positioning and market dynamics
- supply_chain: Supply chain conditions and constraints
- regulation: Regulatory environment and compliance
- trade_policy: Trade policies, tariffs, and geopolitical factors

OUTPUT: JSON array where each object contains:
- factor: One of the factors listed above
- presence: Boolean indicating if factor is discussed
- aggregated_score: Float from -1.0 to +1.0
- sentiment_label: One of strongly_negative, negative, slightly_negative, neutral, slightly_positive, positive, strongly_positive
- sentences: Array of up to 3 most representative sentences
- confidence: Agent's confidence in assessment (low, medium, high)
- justification: Brief rationale for the score

{SENTIMENT_RUBRIC}

INSTRUCTIONS:
- Analyze ALL factors, even if not explicitly mentioned (set presence=false, aggregated_score=0.0 for absent factors).
- For each factor, find the most representative sentences and compute an aggregated sentiment score.
- Consider context and qualifiers when scoring (e.g., "could" vs "will", "modest" vs "significant").
- If a factor has mixed sentiment, note this in the justification and explain the aggregation.
"""
    (out_dir / "prompt_combined.txt").write_text(combined, encoding="utf-8")

    generated_files = [
        *[f"prompt_{f}.txt" for f in FACTORS],
        "prompt_competition_confidence.txt",
        "prompt_outlook_performance.txt",
        "prompt_mixed_sentiment.txt",
        "prompt_combined.txt",
    ]
    print(f"Wrote {len(generated_files)} prompts to {out_dir}:")
    for fname in generated_files:
        print(f"  - {fname}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Generate MD&A prompt templates")
    p.add_argument("out_dir", nargs="?", default="./prompts", help="output directory")
    args = p.parse_args()
    generate_prompts(Path(args.out_dir))
