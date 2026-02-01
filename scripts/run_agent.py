#!/usr/bin/env python3
"""Mock runner that produces predictions for demo evaluation.

This script reads `evaluation/sample_labels.jsonl` (or another input JSONL of GT) and
produces a predictions JSONL where sentiment_score is the GT score plus small noise.

Usage:
  python3 scripts/run_agent.py --input evaluation/sample_labels.jsonl --out evaluation/demo_outputs.jsonl --mock
  python3 scripts/run_agent.py --input evaluation/sample_labels.jsonl --out evaluation/repro_run.jsonl --mock --seed 123
"""
import argparse
import json
import random
from pathlib import Path


def read_jsonl(p: Path):
    out = []
    with p.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    return out


def write_jsonl(path: Path, items):
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")


def mock_predict(gt_records):
    preds = []
    for g in gt_records:
        base = g.get("sentiment_score", 0.0)
        noise = random.uniform(-0.15, 0.15)
        pred_score = max(-1.0, min(1.0, base + noise))
        preds.append({
            "id": g["id"],
            "factor": g.get("factor", "other"),
            "sentiment_score": round(pred_score, 3),
            "support_sentences": [g.get("sentence")],
        })
    return preds


def call_purple_endpoint(endpoint: str, api_key: str, prompt: str):
    """Call a generic Purple Agent HTTP endpoint.

    Expects a JSON response like: {"predictions": [{"id":..., "sentiment_score":..., "support_sentences": [...]}, ...]}
    This is optional and controlled by flags/env vars. If the provider returns a different schema, adapt this function.
    """
    import requests

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {"prompt": prompt}
    resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("predictions", [])


def call_openai(prompt: str, api_key: str, model: str = "gpt-4o-mini"):
    """Call OpenAI completion endpoint (simple example). Returns list of predictions.

    This expects the OpenAI response to contain a JSON payload under `choices[0].message.content`
    that can be parsed into predictions. The exact mapping depends on your prompt design.
    """
    try:
        import openai
    except Exception:
        raise RuntimeError("openai package not installed")
    openai.api_key = api_key
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.0,
    )
    text = resp.choices[0].message.content
    # Expect the model to return JSON
    try:
        parsed = json.loads(text)
        return parsed.get("predictions", [])
    except Exception:
        # fallback: return empty
        return []


def call_anthropic(prompt: str, api_key: str, model: str = "claude-2"):
    """Call Anthropic (Claude) API. Returns list of predictions.

    Expects the response to be JSON with a `predictions` key.
    """
    try:
        from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
    except Exception:
        raise RuntimeError("anthropic package not installed")
    client = Anthropic(api_key=api_key)
    full = HUMAN_PROMPT + prompt + AI_PROMPT
    resp = client.completions.create(model=model, prompt=full, max_tokens=800)
    text = resp.completion
    try:
        parsed = json.loads(text)
        return parsed.get("predictions", [])
    except Exception:
        return []


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="evaluation/sample_labels.jsonl")
    p.add_argument("--out", default="evaluation/demo_outputs.jsonl")
    p.add_argument("--mock", action="store_true")
    p.add_argument("--use-purple", action="store_true", help="Invoke a Purple Agent HTTP endpoint")
    p.add_argument("--purple-endpoint", default=None, help="Purple Agent endpoint URL")
    p.add_argument("--api-key", default=None, help="API key for Purple Agent endpoint")
    p.add_argument("--seed", type=int, default=None, help="Random seed for reproducible mock predictions")
    args = p.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    gt = read_jsonl(Path(args.input))
    if args.use_purple and args.purple_endpoint:
        # Build a prompt for the Purple Agent; here we send the concatenated GT sentences as context
        prompt_lines = [f"ID: {g['id']}\nSentence: {g['sentence']}\nFactor: {g.get('factor','other')}" for g in gt]
        prompt = "\n\n".join(prompt_lines)
        try:
            preds = call_purple_endpoint(args.purple_endpoint, args.api_key, prompt)
        except Exception as e:
            print(f"Purple Agent call failed: {e}. Falling back to mock predictions.")
            preds = mock_predict(gt)
    elif args.use_purple and not args.purple_endpoint:
        print("--use-purple specified but no --purple-endpoint provided. Falling back to mock.")
        preds = mock_predict(gt)
    elif args.mock:
        preds = mock_predict(gt)
    else:
        preds = mock_predict(gt)
    write_jsonl(Path(args.out), preds)
    print(f"Wrote {len(preds)} predictions to {args.out}")


if __name__ == "__main__":
    main()
