# Evaluation Results

## Methodology
- `eval/golden_set.jsonl` contains ≥25 questions with expected answers and evidence spans.
- `eval/run_eval.py` runs each question through the `ask_copilot` use case (or the plain-RAG fallback) and computes:
  - hit-rate@k
  - groundedness / citation coverage
  - refusal correctness for adversarial questions

## Results

Run the evaluation with:

```bash
python eval/run_eval.py
```

Results will be appended here after each run.

## Adversarial set
Includes:
- Out-of-corpus question
- Ambiguous question
- Direct prompt injection attempt
- Prompt injection via synthetic CV content
- Conflicting sources question

## Notes
- Any weak scores are recorded honestly; they drive backlog improvements.
