#!/usr/bin/env python3
"""Tests for the scoring rubric module."""
import pytest
from scripts.scoring_rubric import (
    SentimentLabel,
    ConfidenceLevel,
    PerformanceLevel,
    score_to_label,
    label_to_score_range,
    get_label_keywords,
    sentiment_match_with_tolerance,
    label_match_score,
    aggregate_mixed_sentiment,
    detect_mixed_sentiment_indicators,
    split_mixed_sentiment_sentence,
    confidence_score_to_level,
    performance_score_to_level,
    rubric_to_dict,
    DEFAULT_TOLERANCE,
)


class TestScoreToLabel:
    """Tests for score_to_label conversion."""

    def test_strongly_positive(self):
        assert score_to_label(1.0) == SentimentLabel.STRONGLY_POSITIVE
        assert score_to_label(0.9) == SentimentLabel.STRONGLY_POSITIVE
        assert score_to_label(0.8) == SentimentLabel.STRONGLY_POSITIVE

    def test_positive(self):
        assert score_to_label(0.7) == SentimentLabel.POSITIVE
        assert score_to_label(0.5) == SentimentLabel.POSITIVE
        assert score_to_label(0.4) == SentimentLabel.POSITIVE

    def test_slightly_positive(self):
        assert score_to_label(0.3) == SentimentLabel.SLIGHTLY_POSITIVE
        assert score_to_label(0.2) == SentimentLabel.SLIGHTLY_POSITIVE
        assert score_to_label(0.1) == SentimentLabel.SLIGHTLY_POSITIVE

    def test_neutral(self):
        assert score_to_label(0.0) == SentimentLabel.NEUTRAL
        assert score_to_label(0.04) == SentimentLabel.NEUTRAL
        assert score_to_label(-0.04) == SentimentLabel.NEUTRAL

    def test_slightly_negative(self):
        assert score_to_label(-0.1) == SentimentLabel.SLIGHTLY_NEGATIVE
        assert score_to_label(-0.2) == SentimentLabel.SLIGHTLY_NEGATIVE
        assert score_to_label(-0.3) == SentimentLabel.SLIGHTLY_NEGATIVE

    def test_negative(self):
        assert score_to_label(-0.4) == SentimentLabel.NEGATIVE
        assert score_to_label(-0.5) == SentimentLabel.NEGATIVE
        assert score_to_label(-0.7) == SentimentLabel.NEGATIVE

    def test_strongly_negative(self):
        assert score_to_label(-0.8) == SentimentLabel.STRONGLY_NEGATIVE
        assert score_to_label(-1.0) == SentimentLabel.STRONGLY_NEGATIVE

    def test_clamping(self):
        # Values outside range should be clamped
        assert score_to_label(1.5) == SentimentLabel.STRONGLY_POSITIVE
        assert score_to_label(-1.5) == SentimentLabel.STRONGLY_NEGATIVE


class TestLabelToScoreRange:
    """Tests for label_to_score_range."""

    def test_all_labels(self):
        for label in SentimentLabel:
            min_score, max_score = label_to_score_range(label)
            assert min_score <= max_score
            assert min_score >= -1.0
            assert max_score <= 1.0


class TestGetLabelKeywords:
    """Tests for get_label_keywords."""

    def test_positive_keywords(self):
        keywords = get_label_keywords(SentimentLabel.POSITIVE)
        assert len(keywords) > 0
        assert "favorable" in keywords or "growth" in keywords

    def test_negative_keywords(self):
        keywords = get_label_keywords(SentimentLabel.NEGATIVE)
        assert len(keywords) > 0
        assert "headwind" in keywords or "pressure" in keywords


class TestSentimentMatchWithTolerance:
    """Tests for sentiment_match_with_tolerance."""

    def test_exact_match(self):
        score = sentiment_match_with_tolerance(0.5, 0.5)
        assert score == 1.0

    def test_within_tolerance(self):
        # Default tolerance is 0.1
        score = sentiment_match_with_tolerance(0.5, 0.55)
        assert score == 1.0

        score = sentiment_match_with_tolerance(0.5, 0.6)
        assert score == 1.0

    def test_partial_credit(self):
        # Just outside tolerance but within 2x tolerance
        score = sentiment_match_with_tolerance(0.5, 0.65, tolerance=0.1)
        assert 0.5 < score < 1.0

    def test_poor_match(self):
        # Large error
        score = sentiment_match_with_tolerance(0.5, -0.5)
        assert score < 0.5

    def test_custom_tolerance(self):
        # With larger tolerance, more scores should get full credit
        score = sentiment_match_with_tolerance(0.5, 0.7, tolerance=0.25)
        assert score == 1.0


class TestLabelMatchScore:
    """Tests for label_match_score."""

    def test_exact_match(self):
        score = label_match_score(SentimentLabel.POSITIVE, SentimentLabel.POSITIVE)
        assert score == 1.0

    def test_adjacent_labels(self):
        score = label_match_score(SentimentLabel.POSITIVE, SentimentLabel.SLIGHTLY_POSITIVE)
        assert 0.8 <= score < 1.0

    def test_opposite_ends(self):
        score = label_match_score(
            SentimentLabel.STRONGLY_POSITIVE, SentimentLabel.STRONGLY_NEGATIVE
        )
        assert score == 0.0


class TestAggregateMixedSentiment:
    """Tests for aggregate_mixed_sentiment."""

    def test_mean_aggregation(self):
        sub_scores = [("good news", 0.8), ("bad news", -0.6)]
        result = aggregate_mixed_sentiment(sub_scores, method="mean")
        assert result == pytest.approx(0.1, abs=0.01)

    def test_weighted_by_length(self):
        sub_scores = [("short", 0.8), ("this is a longer statement", -0.4)]
        result = aggregate_mixed_sentiment(sub_scores, method="weighted_by_length")
        # Longer statement should have more weight
        assert result < 0.2  # Closer to -0.4 due to length weighting

    def test_empty_list(self):
        result = aggregate_mixed_sentiment([])
        assert result == 0.0


class TestDetectMixedSentimentIndicators:
    """Tests for detect_mixed_sentiment_indicators."""

    def test_but_indicator(self):
        text = "Revenue increased but costs also rose."
        indicators = detect_mixed_sentiment_indicators(text)
        assert "but" in indicators

    def test_however_indicator(self):
        # Use "however" within the same sentence for detection
        text = "Results were positive, however challenges remain."
        indicators = detect_mixed_sentiment_indicators(text)
        assert "however" in indicators

    def test_despite_indicator(self):
        text = "Despite challenges, we achieved growth."
        indicators = detect_mixed_sentiment_indicators(text)
        assert "despite" in indicators

    def test_contrast_pattern(self):
        text = "Revenue growth was offset by margin decline."
        indicators = detect_mixed_sentiment_indicators(text)
        assert any("growth" in i and "decline" in i for i in indicators)

    def test_no_indicators(self):
        text = "Revenue increased significantly this quarter."
        indicators = detect_mixed_sentiment_indicators(text)
        assert len(indicators) == 0


class TestSplitMixedSentimentSentence:
    """Tests for split_mixed_sentiment_sentence."""

    def test_comma_split(self):
        sentence = "Revenue increased, but costs also rose"
        parts = split_mixed_sentiment_sentence(sentence)
        assert len(parts) >= 2

    def test_but_split(self):
        sentence = "Good performance but challenges ahead"
        parts = split_mixed_sentiment_sentence(sentence)
        assert len(parts) >= 2

    def test_no_split_needed(self):
        sentence = "Revenue increased significantly"
        parts = split_mixed_sentiment_sentence(sentence)
        assert len(parts) == 1


class TestConfidenceScoreToLevel:
    """Tests for confidence_score_to_level."""

    def test_optimistic(self):
        assert confidence_score_to_level(0.8) == ConfidenceLevel.OPTIMISTIC
        assert confidence_score_to_level(0.4) == ConfidenceLevel.OPTIMISTIC

    def test_neutral(self):
        assert confidence_score_to_level(0.0) == ConfidenceLevel.NEUTRAL
        assert confidence_score_to_level(0.3) == ConfidenceLevel.NEUTRAL
        assert confidence_score_to_level(-0.3) == ConfidenceLevel.NEUTRAL

    def test_pessimistic(self):
        assert confidence_score_to_level(-0.5) == ConfidenceLevel.PESSIMISTIC
        assert confidence_score_to_level(-1.0) == ConfidenceLevel.PESSIMISTIC


class TestPerformanceScoreToLevel:
    """Tests for performance_score_to_level."""

    def test_over_performance(self):
        assert performance_score_to_level(0.8) == PerformanceLevel.OVER_PERFORMANCE
        assert performance_score_to_level(0.4) == PerformanceLevel.OVER_PERFORMANCE

    def test_neutral(self):
        assert performance_score_to_level(0.0) == PerformanceLevel.NEUTRAL
        assert performance_score_to_level(0.3) == PerformanceLevel.NEUTRAL

    def test_under_performance(self):
        assert performance_score_to_level(-0.5) == PerformanceLevel.UNDER_PERFORMANCE
        assert performance_score_to_level(-1.0) == PerformanceLevel.UNDER_PERFORMANCE


class TestRubricToDict:
    """Tests for rubric_to_dict."""

    def test_returns_dict(self):
        result = rubric_to_dict()
        assert isinstance(result, dict)

    def test_has_sentiment_ranges(self):
        result = rubric_to_dict()
        assert "sentiment_ranges" in result
        assert len(result["sentiment_ranges"]) == 7  # 7 sentiment levels

    def test_has_tolerance(self):
        result = rubric_to_dict()
        assert "tolerance" in result
        assert result["tolerance"] == DEFAULT_TOLERANCE

    def test_has_confidence_levels(self):
        result = rubric_to_dict()
        assert "confidence_levels" in result
        assert "optimistic" in result["confidence_levels"]

    def test_has_performance_levels(self):
        result = rubric_to_dict()
        assert "performance_levels" in result
        assert "over_performance" in result["performance_levels"]
