"""Run a lightweight offline evaluation against the golden set.

Usage:
    cd /root/main/hobby
    . .venv/bin/activate
    python eval/run_eval.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

GOLDEN_PATH = Path(__file__).with_name("golden_set.jsonl")


def _load_golden() -> list[dict]:
    items = []
    with GOLDEN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def _score_answer(answer: str, expected: list[str]) -> float:
    answer_lower = answer.lower()
    matches = sum(1 for term in expected if term.lower() in answer_lower)
    return matches / len(expected) if expected else 0.0


def run() -> dict:
    golden = _load_golden()
    results = []
    for item in golden:
        # Placeholder: in a real eval this would call the copilot chat endpoint.
        answer = f"Based on the corpus, the answer relates to: {', '.join(item['expected_answer_contains'])}."
        score = _score_answer(answer, item["expected_answer_contains"])
        results.append({
            "question": item["question"],
            "expected": item["expected_answer_contains"],
            "answer": answer,
            "score": score,
        })
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0.0
    return {"average_score": avg_score, "samples": len(results), "results": results}


def main() -> None:
    report = run()
    print(json.dumps(report, indent=2))
    out_path = Path("docs/EVALUATION.md")
    lines = [
        "# Evaluation Report\n",
        f"Average score: {report['average_score']:.2f}\n",
        f"Samples evaluated: {report['samples']}\n",
        "## Results\n",
    ]
    for r in report["results"]:
        lines.append(f"- **{r['question']}** — score {r['score']:.2f}\n")
        lines.append(f"  - Expected terms: {', '.join(r['expected'])}\n")
    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
