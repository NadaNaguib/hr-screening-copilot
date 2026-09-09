# Common Trainee Mistakes — 5 Misconceptions

## Misconception 1: "Prompting the LLM to be unbiased is enough"

**What trainees say**: "I just added 'do not consider race, gender, or age' to the system prompt and the bias problem is solved."

**Why it's wrong**: LLMs are probabilistic. A sufficiently adversarial input can still leak protected attributes into scoring through indirect inference (e.g., names strongly correlated with nationality). Prompting is a soft constraint; deterministic code is a hard constraint.

**How to correct it**: Show the bias_guard implementation — it runs **before** the LLM sees the content. The LLM is never given the opportunity to reason about protected attributes because they are redacted from its input, not just from its output.

---

## Misconception 2: "The human gate is just a UI checkbox"

**What trainees say**: "I can just put an 'Approved' button in the frontend and call it a human gate."

**Why it's wrong**: If the `finalize_shortlist` tool can be called from the backend without the approval state, the gate is theatrical. A clever attacker (or a confused developer) can bypass the UI entirely by calling the API directly.

**How to correct it**: Show `decide_candidate.py` — the `finalize_shortlist` call is conditioned on `task.status in {APPROVED, EDITED_AND_APPROVED}`. The gate lives in the use case, not the router, not the frontend. Always enforce invariants at the deepest trustworthy layer.

---

## Misconception 3: "More agents = better results"

**What trainees say**: "I'll add 10 agents to make the system smarter — a formatter agent, a spell-checker agent, a summarizer agent..."

**Why it's wrong**: Each agent adds latency, token cost, and failure surface. Chaining 10 agents multiplies the probability of hallucination and error. The iteration breaker exists for a reason.

**How to correct it**: Show the orchestrator's `max_iterations` and the degrade path. Discuss the principle: "Every agent should be justified by an audit/control requirement, not a feature wish." The 4 agents in this system each serve a distinct governance purpose.

---

## Misconception 4: "I don't need to log LLM calls — it's just an API"

**What trainees say**: "I'm just calling the Gemini API. I'll log errors if something breaks."

**Why it's wrong**: Without token/cost accounting, you cannot detect runaway costs, compare model performance, debug retrieval failures, or pass a security audit. In regulated industries, every AI decision must be traceable.

**How to correct it**: Show `observability/token_cost.py`. Discuss: what happens when a model version changes silently and your costs triple? What happens when a candidate disputes an AI decision and you need to show exactly what the model saw?

---

## Misconception 5: "Clean Architecture is overkill for an AI project"

**What trainees say**: "I'll just put everything in one FastAPI file. The domain logic is simple."

**Why it's wrong**: When you add a second LLM provider (required by the spec), change from Postgres to a managed vector DB, or swap from FastAPI to another framework, you'll rewrite everything. Worse: you can't test domain logic without a running LLM, which makes CI 10× slower.

**How to correct it**: Show the test suite — `tests/unit/test_review_task_transitions.py` runs in milliseconds with zero infrastructure. Show the `LLMPort` protocol — adding a new provider is a single file with no changes to domain or application code. The upfront cost is ~2h of structure; the ongoing savings are continuous.
