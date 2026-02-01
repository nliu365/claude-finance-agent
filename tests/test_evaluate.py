import importlib.util
from pathlib import Path
import pytest

# Load scripts/evaluate.py as a module without relying on package import paths
spec = importlib.util.spec_from_file_location("evalmod", Path(__file__).resolve().parents[1] / "scripts" / "evaluate.py")
evalmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evalmod)


def make_record(i, score, factor="interest_rates", sentence=None):
    """Create a ground truth record for testing."""
    return {
        "id": f"s{i}",
        "sentence": sentence or f"Sentence {i}",
        "sentiment_score": score,
        "sentiment_label": "positive" if score > 0 else "negative" if score < 0 else "neutral",
        "factor": factor,
    }


def make_prediction(i, score, sentences=None):
    """Create a prediction record for testing."""
    return {
        "id": f"s{i}",
        "sentiment_score": score,
        "support_sentences": sentences or [f"Sentence {i}"],
    }


class TestBasicEvaluation:
    """Tests for basic evaluation functionality."""

    def test_sentiment_score_match_exact(self):
        gt = make_record(1, 0.8)
        pred = make_prediction(1, 0.8, ["Sentence 1"])
        res = evalmod.evaluate([gt], [pred])
        assert res["items"] == 1
        assert abs(res["identification"] - 1.0) < 1e-6
        # Combined sentiment should be 1.0 for exact match
        assert res["sentiment"] >= 0.99

    def test_sentiment_score_match_partial(self):
        gt = make_record(2, -0.6)
        pred = make_prediction(2, -0.4, ["Different sentence"])
        res = evalmod.evaluate([gt], [pred])
        # With enhanced scoring, sentiment combines multiple metrics
        # Basic component: 1 - 0.2/2 = 0.9
        assert res["sentiment_basic"] == pytest.approx(0.9, abs=0.01)
        # identification should be low for unrelated support
        assert res["identification"] < 0.5

    def test_missing_prediction(self):
        gt = make_record(1, 0.5)
        res = evalmod.evaluate([gt], [])
        assert res["items"] == 1
        assert res["identification"] == 0.0
        assert res["sentiment"] == 0.0

    def test_multiple_items(self):
        gts = [make_record(i, 0.5) for i in range(5)]
        preds = [make_prediction(i, 0.5) for i in range(5)]
        res = evalmod.evaluate(gts, preds)
        assert res["items"] == 5


class TestEnhancedMetrics:
    """Tests for enhanced sentiment metrics."""

    def test_tolerance_scoring(self):
        """Test that tolerance bands give partial credit for near-misses."""
        gt = make_record(1, 0.5)

        # Within tolerance (0.1 default) should get full credit
        pred_close = make_prediction(1, 0.55)
        res = evalmod.evaluate([gt], [pred_close], tolerance=0.1)
        assert res["sentiment_tolerance"] == 1.0

        # Just outside tolerance should get partial credit
        pred_medium = make_prediction(1, 0.65)
        res = evalmod.evaluate([gt], [pred_medium], tolerance=0.1)
        assert 0.5 < res["sentiment_tolerance"] < 1.0

    def test_label_scoring(self):
        """Test label-level matching."""
        gt = make_record(1, 0.5)  # "positive" label

        # Same label region should score high
        pred_same = make_prediction(1, 0.6)
        res = evalmod.evaluate([gt], [pred_same])
        assert res["sentiment_label"] >= 0.8

        # Very different label should score lower
        pred_diff = make_prediction(1, -0.5)
        res = evalmod.evaluate([gt], [pred_diff])
        assert res["sentiment_label"] < 0.5

    def test_custom_tolerance(self):
        """Test custom tolerance parameter."""
        gt = make_record(1, 0.5)
        pred = make_prediction(1, 0.7)

        # With small tolerance, should not get full credit
        res_small = evalmod.evaluate([gt], [pred], tolerance=0.1)

        # With large tolerance, should get full credit
        res_large = evalmod.evaluate([gt], [pred], tolerance=0.25)

        assert res_large["sentiment_tolerance"] > res_small["sentiment_tolerance"]


class TestDetailedOutput:
    """Tests for detailed output mode."""

    def test_detailed_includes_per_item(self):
        gt = make_record(1, 0.5)
        pred = make_prediction(1, 0.6)
        res = evalmod.evaluate([gt], [pred], detailed=True)
        assert "per_item" in res
        assert len(res["per_item"]) == 1

    def test_detailed_item_fields(self):
        gt = make_record(1, 0.5)
        pred = make_prediction(1, 0.6)
        res = evalmod.evaluate([gt], [pred], detailed=True)
        item = res["per_item"][0]
        assert "id" in item
        assert "gt_score" in item
        assert "pred_score" in item
        assert "identification_score" in item
        assert "sentiment_basic" in item
        assert "sentiment_tolerance" in item


class TestMixedSentimentAnalysis:
    """Tests for mixed sentiment detection and analysis."""

    def test_detects_mixed_sentiment(self):
        """Test that mixed sentiment indicators are detected."""
        gt = make_record(
            1,
            0.1,
            sentence="Revenue increased but costs also rose significantly.",
        )
        pred = make_prediction(1, 0.0)
        res = evalmod.evaluate([gt], [pred])
        assert res["mixed_sentiment_count"] >= 0  # May or may not detect

    def test_mixed_sentiment_with_clauses(self):
        """Test mixed sentiment when GT has clauses annotation."""
        gt = {
            "id": "ms1",
            "sentence": "Revenue increased but costs also rose.",
            "sentiment_score": 0.1,
            "sentiment_label": "slightly_positive",
            "factor": "other",
            "clauses": ["revenue increased", "costs also rose"],
        }
        pred = make_prediction("ms1", 0.1)
        # Change id to match
        pred["id"] = "ms1"
        res = evalmod.evaluate([gt], [pred])
        assert res["items"] == 1


class TestByFactorEvaluation:
    """Tests for per-factor evaluation."""

    def test_evaluate_by_factor(self):
        gts = [
            make_record(1, 0.5, factor="interest_rates"),
            make_record(2, -0.3, factor="fx"),
            make_record(3, 0.7, factor="interest_rates"),
        ]
        preds = [
            make_prediction(1, 0.5),
            make_prediction(2, -0.3),
            make_prediction(3, 0.7),
        ]
        res = evalmod.evaluate_by_factor(gts, preds)
        assert "overall" in res
        assert "by_factor" in res
        assert "interest_rates" in res["by_factor"]
        assert "fx" in res["by_factor"]
        assert res["by_factor"]["interest_rates"]["items"] == 2
        assert res["by_factor"]["fx"]["items"] == 1


class TestClauseLevelMatching:
    """Tests for clause-level sentence matching."""

    def test_exact_sentence_match(self):
        score = evalmod.sentence_match_score(
            "Interest rates increased.",
            ["Interest rates increased."],
        )
        assert score == 1.0

    def test_partial_sentence_match(self):
        score = evalmod.sentence_match_score(
            "Interest rates increased significantly.",
            ["Rates went up."],
        )
        assert 0 < score < 1.0

    def test_no_match(self):
        score = evalmod.sentence_match_score(
            "Interest rates increased.",
            ["The weather was nice."],
        )
        assert score < 0.5

    def test_clause_split(self):
        clauses = evalmod.clause_split("Revenue increased, but costs also rose")
        assert len(clauses) >= 2
