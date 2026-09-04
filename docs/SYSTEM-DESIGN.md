# System Design

## Part A — Core System

### Components
- React frontend (Vite + TypeScript + Tailwind + shadcn/ui)
- FastAPI presentation layer
- Application use cases (Clean Architecture)
- Domain models and state machines
- Infrastructure adapters (Postgres/pgvector, Gemini SDK/REST, parsers, scheduler)
- LangGraph orchestrator behind `OrchestratorPort`

### Data stores
- PostgreSQL 16 + pgvector for relational + vector data.
- Single database, async SQLAlchemy 2.0 + Alembic migrations.

### Authentication
- JWT access tokens, bcrypt password hashing, role-based route guards.

### Deployment
- `docker compose up --build` brings up db, migrate, api, web.
- Secrets via `.env` only.

## Part B — AI/RAG Extension

### Retrieval
- Hybrid search: pgvector dense similarity + Postgres full-text keyword search, fused with Reciprocal Rank Fusion.
- Optional reranker.
- Chunking strategy: semantic paragraph chunks with overlap; ADR-01 documents the choice.

### Agents
1. `evidence_extractor` — extracts structured evidence from CVs.
2. `bias_guard` — deterministic redaction of protected attributes; audit trail.
3. `rubric_scorer` — deterministic numeric aggregation; LLM writes justification only.
4. `shortlist_drafter` — drafts summary; calls gated `finalize_shortlist` tool only after manager approval.

### Orchestrator
- LangGraph graph with typed Pydantic state.
- Iteration breaker, per-step timeout, retry/backoff, degrade-to-Plain-RAG path.
- `SIMULATE_AGENT_FAILURE` forces degrade path for testing.

## Gap Table
| Requirement | How addressed |
|-------------|---------------|
| ≥2 LLM providers | Two Gemini adapters (SDK + REST) with fallback; ADR-04 |
| Human-in-the-loop | Two-stage review + admin override audit |
| Bias audit | Deterministic redaction + audit rows + separation of duties |
| SLA | Dynamic rules + scheduler escalation |
| Observability | Token/cost accounting + correlation IDs + traces |
