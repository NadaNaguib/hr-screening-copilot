# Learning Outcomes & Assessment Map

## Session: Multi-Agent Orchestration in Production
**Target audience**: Post-graduate developers with basic Python/API knowledge  
**Duration**: 90 minutes (60 min lecture + 30 min lab)

---

## Learning Outcomes

By the end of this session, trainees will be able to:

| # | Outcome | Bloom's Level | Assessment Method |
|---|---------|--------------|-------------------|
| LO1 | Explain the difference between a single LLM call and a multi-agent pipeline | Understand | MCQ + verbal Q&A |
| LO2 | Describe the role and boundaries of each agent in the HR screening system | Understand | Diagram exercise |
| LO3 | Identify where human gates must be enforced (code vs prompt) | Analyze | Code review exercise |
| LO4 | Trace a prompt injection attack through the system's defense layers | Analyze | Lab Exercise 4 |
| LO5 | Implement a new agent in an existing LangGraph pipeline | Apply | Stretch Challenge 1 |
| LO6 | Explain why provider abstraction is necessary for production LLM systems | Evaluate | Essay question |
| LO7 | Evaluate the trade-offs between deterministic and LLM-based bias control | Evaluate | Discussion + written reflection |

---

## Assessment Map

### Formative (during session)
- **Checkpoint questions** after each lab exercise (see lab.md) — verbal answers, instructor-assessed
- **Code navigation** exercises — trainees find and explain specific functions
- **Group discussion**: "Why can't we just prompt the LLM to be unbiased?"

### Summative (post-session, optional)
- **Mini-project** (1 week): Add a new domain to the copilot pattern (e.g., loan underwriting, medical triage). Must include: ≥2 agents, 1 human gate, bias guard, evaluation harness with ≥10 test cases.
- **Written reflection** (500 words): What would you change about this architecture for a team of 10 engineers? What would you keep?

---

## Pre-Session Requirements
Trainees should have:
- [ ] Docker installed and running
- [ ] Basic Python async/await understanding
- [ ] Familiarity with REST APIs
- [ ] Cloned the repository and run `docker compose up` successfully

---

## Session Flow

| Time | Activity | Format |
|------|----------|--------|
| 0–5 min | Hook: "Why single LLM calls fail in enterprise" | Demo |
| 5–20 min | Slides 1–6: Agents, orchestration, human gate | Lecture |
| 20–35 min | Slides 7–11: Bias guard, RAG, injection defense | Lecture |
| 35–45 min | Slides 12–16: Architecture, observability, takeaways | Lecture |
| 45–85 min | Lab exercises 1–5 | Hands-on |
| 85–90 min | Debrief, Q&A, stretch challenge intro | Discussion |
