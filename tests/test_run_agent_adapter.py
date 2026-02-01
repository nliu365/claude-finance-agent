import os
import json
from pathlib import Path

from importlib import util

spec = util.spec_from_file_location("run_agent", Path(__file__).resolve().parents[1] / "scripts" / "run_agent.py")
run_agent = util.module_from_spec(spec)
spec.loader.exec_module(run_agent)


def test_mock_predict_shape():
    # create a tiny GT
    gt = [{"id": "s1", "sentence": "Test sentence.", "sentiment_score": 0.5, "factor": "inflation"}]
    preds = run_agent.mock_predict(gt)
    assert isinstance(preds, list)
    assert preds[0]["id"] == "s1"
    assert "sentiment_score" in preds[0]
    assert "support_sentences" in preds[0]


def test_purple_flags_no_endpoint(tmp_path, monkeypatch):
    # ensure that --use-purple without endpoint falls back to mock
    out = tmp_path / "out.jsonl"
    args = ["--input", "evaluation/sample_labels.jsonl", "--out", str(out), "--use-purple"]
    # run main with monkeypatch argv
    monkeypatch.setattr("sys.argv", ["run_agent.py"] + args)
    run_agent.main()
    assert out.exists()
