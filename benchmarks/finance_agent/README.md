# Finance Agent Benchmark (Ported)

This directory contains a minimal, end-to-end port of the Finance Agent benchmark
(arXiv: 2508.00828) into a runnable Green Agent harness.

## What is included

- A simple tool-augmented agent runner for finance QA.
- Tool adapters for Google search (SerpAPI) and EDGAR (SEC-API).
- A sample questions file to validate the pipeline.
- JSONL output compatible with downstream evaluation scripts.

## Requirements

- Python 3.11+
- One LLM provider API key (OpenAI or Anthropic)
- Optional tool keys:
  - `SERPAPI_API_KEY` for Google search
  - `SEC_API_KEY` for SEC-API (EDGAR search)

## Quick start

```bash
python benchmarks/finance_agent/run_benchmark.py \
  --question-file benchmarks/finance_agent/sample_questions.txt \
  --out benchmarks/finance_agent/outputs.jsonl \
  --provider openai \
  --model gpt-4o-mini \
  --enable-google \
  --enable-edgar
```

## Environment variables

```bash
export OPENAI_API_KEY=your-key
export ANTHROPIC_API_KEY=your-key
export SERPAPI_API_KEY=your-key
export SEC_API_KEY=your-key
```

## Output format (JSONL)

Each line is a JSON object:

```json
{
  "id": "q1",
  "question": "...",
  "answer": "...",
  "sources": ["..."],
  "tool_calls": [{"tool": "google_web_search", "input": "..."}]
}
```

Notes:
- This is a minimal port intended to match the benchmark workflow and tool set.
- Replace `sample_questions.txt` with the official benchmark questions when available.
