# Reproducibility Evidence

Two runs of the same configuration (mock Purple Agent with fixed seed) produce identical outputs and evaluation metrics.

## Commands

```bash
python scripts/run_agent.py \
  --input evaluation/sample_labels.jsonl \
  --out evaluation/repro_run_1.jsonl \
  --mock \
  --seed 123

python scripts/run_agent.py \
  --input evaluation/sample_labels.jsonl \
  --out evaluation/repro_run_2.jsonl \
  --mock \
  --seed 123

PYTHONPATH=. python scripts/evaluate.py \
  --gt evaluation/sample_labels.jsonl \
  --pred evaluation/repro_run_1.jsonl \
  > evaluation/repro_eval_1.json

PYTHONPATH=. python scripts/evaluate.py \
  --gt evaluation/sample_labels.jsonl \
  --pred evaluation/repro_run_2.jsonl \
  > evaluation/repro_eval_2.json
```

## Checksums (SHA-256)

```
8b49a886ed99c694a1321c501b1a48efd62dd79c31bb60ccdf5ae7157fd57ded  evaluation/repro_run_1.jsonl
8b49a886ed99c694a1321c501b1a48efd62dd79c31bb60ccdf5ae7157fd57ded  evaluation/repro_run_2.jsonl
f5789a6a20860504d0ecb5c3228e140d51e87ba9cab1cc9fb3eb1df7e13bb5a1  evaluation/repro_eval_1.json
f5789a6a20860504d0ecb5c3228e140d51e87ba9cab1cc9fb3eb1df7e13bb5a1  evaluation/repro_eval_2.json
```
