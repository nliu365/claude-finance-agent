# Baseline Purple Agent (A2A-Compatible)

This folder contains a minimal Purple Agent HTTP server that returns predictions in an A2A-compatible schema.

## API

- **POST /**
  - Request JSON: `{ "prompt": "..." }`
  - Response JSON: `{ "predictions": [{ "id": "...", "factor": "other", "sentiment_score": 0.0, "support_sentences": ["..."] }] }`

The server extracts `ID:` and `Sentence:` lines from the prompt and emits one prediction per ID.

## Run

```bash
python purple_agent/server.py
```

## Connect from the Green Agent runner

```bash
python scripts/run_agent.py \
  --input evaluation/sample_labels.jsonl \
  --out evaluation/purple_outputs.jsonl \
  --use-purple \
  --purple-endpoint http://localhost:8000
```
