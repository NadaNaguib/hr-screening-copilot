# Business Requirements Document (BRD)

> **Project**: Domain Copilot for HR Screening (Variant D6 + T5)  
> **Candidate**: Nada Naguib | ITI Dev Instructor Task  
> **Target Version**: 1.0.0  
> **Status**: Production-Ready / Implemented  
> **Repository**: [hr-screening-copilot](https://github.com/NadaNaguib/hr-screening-copilot)

---

## 1. Executive Summary & Purpose

The **HR Screening Domain Copilot** is an enterprise-grade, agentic Retrieval-Augmented Generation (RAG) platform tailored for high-volume technical talent screening. The platform addresses the dual challenges of recruitment throughput and decision fairness:

1. **Recruiter Fatigue & Throughput**: Evaluating hundreds of technical resumes against complex rubrics requires significant recruiter effort, leading to screening bottlenecks.
2. **Fairness & Bias Mitigation**: Unconscious human and algorithmic bias on protected attributes (gender, nationality, age, religion) poses severe ethical and legal risks.
3. **Accountability & Control (Human-in-the-Loop)**: Purely autonomous AI decision-making is unacceptable in talent acquisition. The platform implements **Variant D6** (Talent Screening: Evidence Extraction, Rubric Scoring, Shortlist Drafting) combined with **T5 as a full product** (Human Review Queue with SLA timers, role-based approval stages, assignment, and escalation).

---

## 2. Stakeholder Personas

| Persona | Role Key | Primary Responsibilities | Core Jobs to Be Done (JTBD) |
|---|---|---|---|
| **HR Recruiter** | `hr_recruiter` | Talent sourcing, initial triage, CV parsing | Upload resumes, initiate automated screening, review extracted evidence, assign priority, forward qualified candidates to hiring managers. |
| **Hiring Manager** | `hiring_manager` | Final hiring authority, team lead | Review shortlist drafts and rubric justifications, inspect cited evidence, approve or reject candidates with feedback, export final shortlists. |
| **Platform Admin** | `admin` | System operations, compliance, break-glass | Configure global and job-specific SLA rules, monitor token consumption and costs, manage system users, execute audited break-glass overrides. |

---

## 3. Scope Definition

### 3.1 In-Scope
- Automated ingestion of PDF and plaintext CVs with SHA-256 cryptographic deduplication.
- Dense (pgvector HNSW) and keyword (PostgreSQL tsvector) hybrid search fused via Reciprocal Rank Fusion (RRF).
- LangGraph-orchestrated 4-agent pipeline: Evidence Extractor, Deterministic Bias Guard, Rubric Scorer, and Shortlist Drafter.
- Graceful degradation paths from Agentic RAG to Plain RAG during model rate-limiting or service disruptions.
- Two-stage human approval workflow with role-based separation of duties (Recruiter triage → Manager decision).
- Full T5 Review Queue product: priority assignment, SLA countdown timers, auto-escalation engine, reviewer analytics.
- Real-time Server-Sent Events (SSE) Copilot Chat with persistent session management and grounded citation cards.
- Comprehensive security guardrails: prompt injection defenses, PII leakage prevention, protected attribute refusal.
- Live observability and token cost ledger with per-model breakdown and connection health diagnostics.
- Synthetic candidate mimicry and cascade deletion for vacancies and applicant records.

### 3.2 Out-of-Scope (Explicit)
- Direct automated candidate emailing or external calendar scheduling (deferred to enterprise ATS integration).
- Autonomous hiring/rejection without human reviewer sign-off (prohibited by system business rules).
- Scraping external social media (LinkedIn, GitHub) without explicit candidate consent.
- Direct video/audio interview analysis (platform scope is strictly document-grounded evaluation).
- Multi-tenant enterprise billing isolation (single-tenant architecture deployed for MVP).

---

## 4. Business Rules

| Rule ID | Rule Name | Description |
|---|---|---|
| **BRULE-01** | **Human Decision Supremacy** | AI agents may only draft recommendations, extract evidence, and compute rubric justifications. Final candidate decisions (`APPROVED` or `REJECTED`) require authenticated human sign-off. |
| **BRULE-02** | **Deterministic Bias Exclusion** | Protected demographic attributes (gender, age, nationality, religion, marital status) must be deterministically redacted BEFORE rubric scoring and LLM synthesis. An audit log row must be recorded for every redaction. |
| **BRULE-03** | **Separation of Review Duties** | An HR Recruiter may only forward a candidate to the Hiring Manager or reject at triage (`PENDING_TRIAGE` → `PENDING_MANAGER_REVIEW` or `REJECTED`). Only a Hiring Manager can mark a candidate `APPROVED`. |
| **BRULE-04** | **Audited Break-Glass Override** | Platform Admins may override any task state at any time, but must provide a mandatory justification text that is permanently recorded in the immutable task audit log. |
| **BRULE-05** | **Strict SLA Hierarchy** | SLA breach calculations evaluate job-specific SLA overrides first; if no job-level rule exists, the global SLA default for that priority level is enforced. |
| **BRULE-06** | **Deduplication Integrity** | Uploaded documents matching an existing SHA-256 hash within the candidate pool are rejected immediately to prevent redundant vector storage and duplicate pipelines. |
| **BRULE-07** | **Gated Shortlist Finalization** | A job shortlist can only transition from `draft` to `finalized` after the associated review task achieves `APPROVED` status from the Hiring Manager. |
| **BRULE-08** | **Grounded Evidence Mandate** | Copilot Chat responses must be strictly grounded in retrieved vector/FTS document chunks with verifiable citation metadata (source file and page number). |
| **BRULE-09** | **Adversarial Query Immunity** | Queries attempting to extract PII (candidate email, phone, home address), force prompt injection, or demand demographic filtering must be immediately refused by security guardrails. |
| **BRULE-10** | **Cascade Lifecycle Cleanup** | Deleting a job vacancy or candidate must cleanly cascade to unlinking or purging associated tasks, document chunks, vectors, rubrics, and shortlists. |

---

## 5. Functional Requirements & Acceptance Criteria

### BR-01: Document Ingestion & Deduplication
- **Description**: The system must ingest candidate CVs (PDF, TXT) and job descriptions, extract raw text, and deduplicate files cryptographically.
- **Acceptance Criteria**:
  - `AC-01.1`: Uploading a file computes the SHA-256 hash. Duplicate hashes reject the upload with HTTP 409 Conflict.
  - `AC-01.2`: Text parser extracts body text, skills, and metadata without data truncation.
  - `AC-01.3`: Candidates appear immediately in the talent pool associated with the target job vacancy.

### BR-02: Hybrid Vector Retrieval & Chunking
- **Description**: Candidate documents must be indexed using semantic chunking and retrieved using dense and sparse hybrid search.
- **Acceptance Criteria**:
  - `AC-02.1`: Documents are split into 512-token chunks with 50-token overlap.
  - `AC-02.2`: Embeddings are generated using Gemini `text-embedding-004` (768 dimensions) and indexed in pgvector using HNSW.
  - `AC-02.3`: Keyword search uses PostgreSQL `tsvector` with `english` dictionary.
  - `AC-02.4`: Reciprocal Rank Fusion (RRF with $k=60$) combines dense and sparse ranks into a single unified score.

### BR-03: Multi-Agent Screening Pipeline (Variant D6)
- **Description**: An automated screening pipeline orchestrates four specialized agents in a state graph to evaluate candidate resumes against rubrics.
- **Acceptance Criteria**:
  - `AC-03.1`: `evidence_extractor` maps resume passages to job rubric criteria with quotes and source locations.
  - `AC-03.2`: `bias_guard` applies deterministic regex-based redaction of protected attributes and writes redaction logs before scoring.
  - `AC-03.3`: `rubric_scorer` computes deterministic weighted numeric scores ($[0.0, 1.0]$) while delegating qualitative justification text to the LLM.
  - `AC-03.4`: `shortlist_drafter` compiles a structured candidate summary and draft recommendation.
  - `AC-03.5`: LangGraph orchestrator enforces an iteration breaker ($\le 10$ steps) and a 30s per-step timeout, automatically falling back to Plain RAG if agent limits are exceeded.

### BR-04: Human Review Queue (T5 Full Product)
- **Description**: A dedicated review queue supporting task assignment, priority levels, SLA countdowns, auto-escalation, and role-based review actions.
- **Acceptance Criteria**:
  - `AC-04.1`: Review tasks render candidate full names, job titles, priority badges, and remaining SLA time.
  - `AC-04.2`: HR Recruiters see "Forward to Manager" and "Reject" buttons with reason capture.
  - `AC-04.3`: Hiring Managers see "Approve", "Reject", and "Edit & Approve" buttons with feedback capture.
  - `AC-04.4`: Admins have an "Admin Override" button with mandatory audit reason logging.
  - `AC-04.5`: Tasks breaching SLA thresholds display visual red escalation warnings.

### BR-05: Configurable SLA Engine & Auto-Escalation
- **Description**: System allows configuring SLA response deadlines by priority and automatically escalates overdue tasks.
- **Acceptance Criteria**:
  - `AC-05.1`: Admin can define global SLA defaults for `HIGH`, `MEDIUM`, and `LOW` priorities (triage hours and decision hours).
  - `AC-05.2`: Admin can create per-job SLA overrides that take precedence over global rules.
  - `AC-05.3`: Background scheduler evaluates deadlines and marks `triage_escalated_at` or `decision_escalated_at` when deadlines elapse.

### BR-06: Copilot Chat with Persistent Sessions & Grounding
- **Description**: An interactive conversational assistant answering natural language questions about applicants, backed by grounded evidence citations.
- **Acceptance Criteria**:
  - `AC-06.1`: Responses stream in real-time via Server-Sent Events (SSE).
  - `AC-06.2`: Chat sessions are persisted in local storage with the ability to create, switch, and delete conversations.
  - `AC-06.3`: Responses include clickable citation source cards showing document name, page number, and quoted excerpt.
  - `AC-06.4`: Security guardrails intercept adversarial prompts (PII, prompt injection, demographic bias) and refuse them gracefully.

### BR-07: Shortlist Export
- **Description**: Approved candidates can be exported in standardized formats for external hiring workflows.
- **Acceptance Criteria**:
  - `AC-07.1`: Shortlist export endpoint `GET /api/v1/shortlist/{job_id}/export?format=csv` generates RFC 4180-compliant CSV data.
  - `AC-07.2`: Frontend provides a one-click CSV export button on the Jobs & Candidates dashboard.

### BR-08: Observability & AI Control Panel
- **Description**: Comprehensive tracking of token usage, financial expenditure, and system diagnostics.
- **Acceptance Criteria**:
  - `AC-08.1`: Every LLM call records prompt tokens, completion tokens, model name, and estimated cost in USD to a persistent ledger.
  - `AC-08.2`: AI Control Panel renders dynamic KPI cards, per-model cost tables, and real-time invocation history.
  - `AC-08.3`: Live connectivity diagnostic tests Gemini API availability and response latency on demand.

### BR-09: User Management & RBAC
- **Description**: Administrative user provisioning, authentication, and role lifecycle management.
- **Acceptance Criteria**:
  - `AC-09.1`: Secure user creation with email, role (`admin`, `hr_recruiter`, `hiring_manager`), and password hashing.
  - `AC-09.2`: User deletion capability with protection against self-deletion.
  - `AC-09.3`: JWT authentication protects all private API routes with strict role enforcement.

### BR-10: Synthetic Candidate Mimicry & Matching
- **Description**: Ability to generate realistic synthetic applicant profiles to test job rubrics and screening pipelines.
- **Acceptance Criteria**:
  - `AC-10.1`: "Mimic CV & Match" button on any job vacancy generates a synthetic candidate with tailored skills and work history.
  - `AC-10.2`: Synthetic candidate is immediately embedded, indexed, and linked to the vacancy for screening.

### BR-11: Cascade Deletion & Vacancy Lifecycle
- **Description**: Complete cleanup of vacancies and candidate entities to prevent orphaned records.
- **Acceptance Criteria**:
  - `AC-11.1`: Deleting a job vacancy cascades to remove or unlink review tasks, rubrics, chunks, and shortlists.
  - `AC-11.2`: Deleting a candidate purges their document chunks, embeddings, and review task history.

---

## 6. Non-Functional Requirements (NFRs)

| NFR ID | Category | Requirement | Verification Method |
|---|---|---|---|
| **NFR-01** | **Architecture** | Adherence to Clean Architecture principles: Domain layer has zero external dependencies; Application layer depends only on Domain; Infrastructure implements Application ports. | Code inspection & dependency graph analysis. |
| **NFR-02** | **Performance** | Hybrid vector retrieval latency $\le 300\text{ ms}$ for pools up to 10,000 document chunks. | Database query profiling with `EXPLAIN ANALYZE`. |
| **NFR-03** | **Security** | Zero hardcoded API keys or secrets in source code; all credentials read from environment variables; password hashing via bcrypt ($\text{cost}\ge 12$). | Gitleaks scanning in CI and code review. |
| **NFR-04** | **Reliability** | Graceful degradation to Plain RAG if Gemini API times out, returns 429 (rate-limited), or fails. | Orchestrator fallback tests with `SIMULATE_AGENT_FAILURE=true`. |
| **NFR-05** | **Deployability** | Single-command deployment using Docker Compose bringing up PostgreSQL, Alembic migrations, FastAPI backend, and Nginx web server. | Fresh environment `docker compose up --build` smoke test. |
| **NFR-06** | **Maintainability** | Comprehensive test coverage with unit, integration, and evaluation suites; strict type hints verified by `mypy` and linted by `ruff`. | CI pipeline execution (`ruff check`, `mypy`, `pytest`). |
| **NFR-07** | **Auditability** | Every state transition, bias redaction, and break-glass override must generate an immutable audit log row with timestamp, actor ID, and rationale. | PostgreSQL audit log table verification. |
| **NFR-08** | **Usability** | Modern responsive React SPA built with Tailwind CSS, custom design tokens, SLA countdown timers, and persistent conversation history. | Automated browser verification via subagents. |

---

## 7. Traceability Matrix

This matrix maps every Business Requirement (BR) to its architectural component, implementation evidence, and verification status.

| Requirement ID | Priority | Module / Layer | Implementation Files & Endpoints | Verification Evidence | Status |
|---|---|---|---|---|---|
| **BR-01** | High | Ingestion / API | `src/copilot/infrastructure/parsing/`, `POST /api/v1/candidates/upload` | SHA-256 collision tests, candidate upload UI | ✅ Implemented |
| **BR-02** | High | Retrieval / DB | `src/copilot/infrastructure/retrieval/hybrid.py`, pgvector HNSW | Hybrid search queries, RRF fusion benchmarks | ✅ Implemented |
| **BR-03** | High | Agents / LangGraph | `src/copilot/agents/`, `POST /api/v1/pipeline/run` | Multi-agent execution, token cost logging | ✅ Implemented |
| **BR-04** | High | Review Queue (T5) | `frontend/src/pages/ReviewQueue.tsx`, `routers/review_queue.py` | UI role buttons, SLA countdown badges | ✅ Implemented |
| **BR-05** | Medium | SLA Engine | `src/copilot/domain/sla_rule.py`, `routers/admin_sla_rules.py` | SLA countdown timers, case-insensitive rules | ✅ Implemented |
| **BR-06** | High | Chat / SSE | `src/copilot/application/use_cases/ask_copilot.py`, `CopilotChat.tsx` | SSE streaming test, persistent chat history | ✅ Implemented |
| **BR-07** | Medium | Shortlist / Export | `src/copilot/presentation/routers/review_queue.py`, `export_shortlist.py` | `GET /shortlist/{id}/export?format=csv` | ✅ Implemented |
| **BR-08** | High | Observability | `src/copilot/infrastructure/observability/token_cost.py`, `AISettings.tsx` | Dynamic ledger file, live KPI dashboard | ✅ Implemented |
| **BR-09** | High | Auth & Admin | `src/copilot/presentation/routers/admin_users.py`, `UserManagement.tsx` | JWT bearer tests, user remove modal | ✅ Implemented |
| **BR-10** | High | Candidate Mimic | `src/copilot/application/use_cases/mimic_candidate.py`, `routers/jobs.py` | 1-click "Mimic CV & Match" button | ✅ Implemented |
| **BR-11** | High | Cascade Lifecycle | `DELETE /api/v1/jobs/{id}`, `DELETE /api/v1/candidates/{id}` | Cascade unlinking of tasks, rubrics, chunks | ✅ Implemented |
