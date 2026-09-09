# Domain Copilot — Master Project Status & Plan

> **Variant**: D6 (HR Talent Screening) + T5 (Human Review Queue as full product)
> **Last updated**: 2026-09-09 | **Deadline**: Day 12 from invitation (23:59 Cairo time)
> **Repo**: https://github.com/NadaNaguib/hr-screening-copilot
> **Live dev server**: http://152.53.183.220:3000

---

## Git Rubric Snapshot

| Metric | Required | Current | Status |
|---|---|---|---|
| Commits on `main` | ≥ 30 | 41 | ✅ |
| Active days | ≥ 6 | 6 (Sep 4–9) | ✅ |
| Merged PRs (merge commits) | ≥ 8 | 6 | ❌ Need +2 |
| Feature branches | 8 | 8 | ✅ |
| CI green on `main` | Required | Defined (not locally verified) | ⚠️ |

---

## ITI Spec — Deliverables Checklist

### Deliverable 1 · Public GitHub Repository
- [x] Source, Docker, migrations, seed, agentic config committed
- [ ] Repo must be **public for 30 days** — verify visibility

### Deliverable 2 · BRD (`docs/BRD.md`)
- [x] Context, personas, objectives
- [ ] Uniquely-ID'd requirements (BR-xx) — MISSING
- [ ] Acceptance criteria per requirement — MISSING
- [ ] Explicit out-of-scope section — MISSING
- [ ] Business rules section — MISSING
- [ ] Traceability matrix (BR-xx → implemented/partial/deferred → evidence) — MISSING ENTIRELY

### Deliverable 3 · System Design (`docs/SYSTEM-DESIGN.md`)
- [x] Part B (MVP) with thin gap table
- [ ] Part A — Target architecture (unconstrained: gateway, rate limiting, secrets manager, broker, autoscaling, caching, managed vector DB, observability stack, CI/CD, DR/backup, cost model) — MISSING
- [ ] Gap table with: why deferred | interim mitigation | effort+cost to close — MISSING reasoning columns
- [ ] Design decisions with alternatives considered and rejected — MISSING

### Deliverable 4 · Architecture Docs (`docs/ARCHITECTURE.md`)
- [x] C4 Level 1 & 2 (text-only, minimal)
- [x] 4 ADRs (ADR-01 to ADR-04)
- [ ] C4 Level 3 (Component) — MISSING
- [ ] Sequence diagram (full agentic workflow + approval gate + streaming) — MISSING
- [ ] Data-flow diagram with trust boundaries — MISSING
- [ ] ER diagram — MISSING
- [ ] Layer-dependency diagram — MISSING
- [ ] Diagram SOURCE committed (Mermaid/PlantUML) — MISSING (text-only now)

### Deliverable 5 · README
- [x] Quick start (docker compose up)
- [ ] Prerequisites list — MISSING
- [ ] Every environment variable documented — MISSING
- [ ] How to obtain free API keys — MISSING
- [ ] How to run with local model (no key) — MISSING
- [ ] How to run tests + eval harness — MISSING
- [ ] Seeded demo accounts table — MISSING
- [ ] Troubleshooting section — MISSING
- [ ] 5-Minute Demo Path (numbered script, every core capability) — MISSING
- [ ] Video links — MISSING

### Deliverable 6 · Security & Evaluation Reports
- [x] SECURITY.md — OWASP Web + LLM mapping present
- [ ] EVALUATION.md — only 5 samples, need ≥ 25 incl. adversarial + failure analysis — MISSING
- [ ] golden_set.jsonl — expand from 5 to ≥ 25 — MISSING

### Deliverable 7 · Teaching Pack (`teaching/`) — NON-NEGOTIABLE
- [ ] ENTIRE DIRECTORY MISSING
- [ ] 15–25 slides for 90-min post-graduate session
- [ ] Hands-on lab sheet (expected outputs, ≥3 stretch challenges, answer key)
- [ ] Learning outcomes & assessment map
- [ ] Common trainee mistakes (5 misconceptions + corrections)

### Deliverable 8 · Two Videos — NON-NEGOTIABLE
- [ ] 5–8 min product demo (ingest, answer+citations, refusal, multi-agent, approval gate, trace) — MISSING
- [ ] 10 min teaching sample (face+voice) — MISSING
- [ ] Both links in README — MISSING

### Deliverable 9 · Deployment (optional, strongly valued)
- [x] Dev server at http://152.53.183.220:3000
- [ ] Free-tier public deployment (Render/Railway/Fly.io)

### Additional Non-Negotiable
- [ ] `docs/AI-USAGE-LOG.md` — MISSING

---

## Functional Requirements Status

| FR | Requirement | Status | Gap |
|----|-------------|--------|-----|
| FR-1 | Document ingestion (PDF/DOCX, SHA-256 dedup, parse, skills) | ✅ | — |
| FR-2 | Agentic pipeline (evidence, bias-guard, rubric, shortlist) | ✅ | — |
| FR-3 | Two-stage review (recruiter→manager→admin override) | ✅ | — |
| FR-4 | SLA rules (configurable, scheduler, auto-escalation) | ⚠️ | SLA timer not shown in UI |
| FR-5 | Human review queue (T5: assignment, priority, SLA timers, escalation, stats) | ⚠️ | Assignment, SLA timers UI, reviewer stats, escalation badge missing |
| FR-6 | Copilot chat (streaming SSE, RAG, citations) | ✅ | — |
| FR-7 | Export shortlist PDF/CSV | ❌ | use-case exists, no HTTP endpoint, no frontend button |
| FR-8 | Observability (token/cost, traces, correlation IDs) | ✅ | — |
| FR-9 | Security (RBAC, input validation, prompt injection, PII audit) | ✅ | — |
| FR-10 | Evaluation ≥ 25 golden Q/A incl. adversarial | ❌ | Only 5, none adversarial |

---

## Active Issues & Fixes (Session 7 Tracking)

| ID | Issue Description | Spec Ref | Status |
|---|---|---|---|
| **ISSUE-01** | Job visibility, CV generation/matching, delete Job & delete Candidate | FR-1, UI | 🟡 In Progress |
| **ISSUE-02** | Duplicate "Senior Full Stack" entries in job dropdown | Data/Seed | 🟡 In Progress |
| **ISSUE-03** | "Run Pipeline" returns 500 Internal Server Error | FR-2, Pipeline | 🟡 In Progress |
| **ISSUE-04** | Copilot Chat: SSE streaming text display, save chat history, citations UI | FR-6, Chat | 🟡 In Progress |
| **ISSUE-05** | Review Queue: Candidate Name instead of UUID, Reviewer Action Buttons (T5) | FR-5, T5 Queue | 🟡 In Progress |
| **ISSUE-06** | AI Control Panel: replace static metrics with dynamic live ledger data | FR-8, Admin | 🟡 In Progress |
| **ISSUE-07** | User Management: add Delete/Remove User capability | Admin RBAC | 🟡 In Progress |
| **ISSUE-08** | SLA Tab: `'HIGH' is not a valid Priority` case crash + metric explanations | FR-4, SLA | 🟡 In Progress |

---

## Implementation Plan (Ordered by Priority)

### 🔴 P1 · Evaluation Set Expansion — Est. 2h [STARTED Sep 9]
- [ ] Expand `eval/golden_set.jsonl` to ≥ 25 Q/A pairs
- [ ] Include adversarial: prompt injection, protected attributes, hallucination traps
- [ ] Include edge cases: unknown candidates, out-of-scope, multi-hop
- [ ] Re-run eval harness, update `docs/EVALUATION.md` with real numbers + failure analysis

### 🔴 P2 · Teaching Pack (`teaching/`) — Est. 4h [STARTED Sep 9]
- [ ] `teaching/slides.md` — 15–25 slides on "Multi-Agent Orchestration in HR Screening"
- [ ] `teaching/lab.md` — hands-on lab, expected outputs, ≥3 stretch challenges
- [ ] `teaching/answer-key.md`
- [ ] `teaching/learning-outcomes.md`
- [ ] `teaching/common-mistakes.md` — 5 misconceptions + corrections

### 🔴 P3 · AI Usage Log — Est. 30min [STARTED Sep 9]
- [ ] Create `docs/AI-USAGE-LOG.md`

### 🔴 P4 · Additional Merged PRs (need +2) — Est. 30min
- [ ] Branch 8: `feat/eval-and-teaching` — merge Sep 9
- [ ] Branch 9: `feat/docs-overhaul` — merge Sep 9

### �� P5 · T5 Queue Full Product — Est. 3h
- [ ] SLA deadline column + time-remaining countdown in ReviewQueue.tsx
- [ ] Escalation badge in queue UI
- [ ] Reviewer stats page (wire compute_reviewer_stats.py → frontend)
- [ ] Task assignment dropdown in queue

### 🟠 P6 · Export Shortlist (FR-7) — Est. 1.5h
- [ ] Add `GET /api/v1/shortlist/{job_id}/export?format=csv` endpoint
- [ ] Wire existing `export_shortlist.py` use-case
- [ ] Frontend export button on Jobs & Candidates page

### 🟠 P7 · BRD Overhaul — Est. 2h
- [ ] Add BR-xx IDs, acceptance criteria, out-of-scope, business rules, assumptions, risks
- [ ] Add traceability matrix

### 🟠 P8 · System Design Overhaul — Est. 2h
- [ ] Add Part A (target unconstrained architecture)
- [ ] Expand gap table with reasoning, deferred rationale, effort+cost

### 🟠 P9 · Architecture Diagrams — Est. 2h
- [ ] C4 Level 3 in Mermaid
- [ ] Sequence diagram (agentic workflow + approval gate + streaming)
- [ ] Data-flow with trust boundaries
- [ ] ER diagram
- [ ] Layer-dependency diagram

### 🟠 P10 · README Overhaul — Est. 1.5h
- [ ] Prerequisites, all env vars, API key instructions, local model instructions
- [ ] How to run tests + eval harness
- [ ] Demo accounts table
- [ ] Troubleshooting section
- [ ] 5-Minute Demo Path (numbered script)
- [ ] Video placeholder links

### 🟡 P11 · Docker smoke-test — Est. 30min
- [ ] `docker compose up --build` fresh clone verification

### 🟡 P12 · Deployment — Est. 2h (optional, strongly valued)
- [ ] Deploy to Render/Railway/Fly.io free tier
- [ ] Update README with live URL + credentials

---

## Session Log

| Date | Session | Work Done |
|---|---|---|
| Sep 4 | 1 | Scaffold, docs, Docker, CI, deps (branch feat/project-scaffold) |
| Sep 5 | 2 | Domain models, ORM, Alembic, backend services, ports, use-cases, agents, auth (branches feat/domain-models, feat/backend-services, feat/auth-and-api) |
| Sep 6 | 3 | Frontend SPA React+Vite+Tailwind+shadcn, auth, RBAC, tests (branch feat/frontend-spa) |
| Sep 7 | 4 | Job form (description+skills), queue priority display (branch feat/job-form-and-queue-priority) |
| Sep 8 | 5 | Editable priority, DB session fix, pgvector raw SQL, Gemini CV extraction (branch feat/editable-priority-and-pipeline-test) |
| Sep 9 | 6 | Full gap analysis vs ITI spec, created PROJECT_STATUS.md; implementing P1-P10 |

---

## Known Technical Debt

| Issue | Impact | Fix |
|---|---|---|
| Tests fail without venv (`ModuleNotFoundError: copilot`) | CI local run broken | `pip install -e .` or activate `.venv` first |
| `reviewer_stats.py` router is stub (574 bytes) | Stats page broken | Wire `compute_reviewer_stats.py` use-case |
| `export_shortlist.py` use-case exists, no HTTP endpoint | FR-7 unreachable | Add router endpoint |
| SLA timers backend only, not in queue UI | T5 gap | Add deadline to queue API + countdown in UI |
| 5 golden Q/A samples (need ≥ 25) | Eval fails spec | Expand `golden_set.jsonl` |
| No `teaching/` directory | Non-negotiable | Create entire teaching pack |
| No `AI-USAGE-LOG.md` | Non-negotiable | Create and maintain |
| BRD lacks BR-xx IDs + traceability matrix | Deliverable 2 fails | Rewrite BRD |
| ARCHITECTURE.md text-only, no Mermaid source | Deliverable 4 fails | Add Mermaid diagrams |
| README missing 5-min demo path, env vars, accounts | Deliverable 5 incomplete | Overhaul README |
