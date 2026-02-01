#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from benchmarks.finance_agent.agent import FinanceAgent


def read_questions(path: Path):
    questions = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                qid, question = parts
            else:
                qid, question = f"q{len(questions)+1}", parts[0]
            questions.append({"id": qid, "question": question})
    return questions


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--question-file", required=True)
    p.add_argument("--out", default="benchmarks/finance_agent/outputs.jsonl")
    p.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--enable-google", action="store_true")
    p.add_argument("--enable-edgar", action="store_true")
    p.add_argument("--serpapi-key", default=None)
    p.add_argument("--sec-api-key", default=None)
    p.add_argument("--user-agent", default=None)
    args = p.parse_args()

    agent = FinanceAgent(
        provider=args.provider,
        model=args.model,
        enable_google=args.enable_google,
        enable_edgar=args.enable_edgar,
        serpapi_key=args.serpapi_key,
        sec_api_key=args.sec_api_key,
        user_agent=args.user_agent,
    )

    questions = read_questions(Path(args.question_file))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for q in questions:
            answer, tool_calls, sources = agent.answer(q["question"])
            record = {
                "id": q["id"],
                "question": q["question"],
                "answer": answer,
                "sources": sources,
                "tool_calls": tool_calls,
            }
            f.write(json.dumps(record) + "\n")

    print(f"Wrote {len(questions)} answers to {out_path}")


if __name__ == "__main__":
    main()
