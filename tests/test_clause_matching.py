from importlib import util
from pathlib import Path

spec = util.spec_from_file_location("evalmod", Path(__file__).resolve().parents[1] / "scripts" / "evaluate.py")
evalmod = util.module_from_spec(spec)
spec.loader.exec_module(evalmod)


def test_clause_split_and_score():
    gt = "We expect modest revenue growth as pricing improvements offset cost pressures."
    candidates = ["Pricing improvements offset cost pressures."]
    score = evalmod.sentence_match_score(gt, candidates)
    assert score > 0.5

def test_clause_no_match():
    gt = "Interest rates will materially harm our business."
    candidates = ["We see no impact from interest rates."]
    score = evalmod.sentence_match_score(gt, candidates)
    assert score < 0.5
