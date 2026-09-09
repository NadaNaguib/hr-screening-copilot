# Architecture Documentation

## C4 Level 1 — System Context

```mermaid
C4Context
    title System Context — Domain Copilot HR Screening

    Person(recruiter, "HR Recruiter", "Triages candidates, sets priority, uploads CVs")
    Person(manager, "Hiring Manager", "Makes final approve/reject decisions")
    Person(admin, "Admin", "Manages users, SLA rules, AI config, break-glass override")

    System(copilot, "Domain Copilot", "Agentic RAG platform for HR screening with human-in-the-loop")

    System_Ext(gemini, "Google Gemini API", "LLM for evidence extraction, rubric scoring, embeddings")
    System_Ext(github, "GitHub", "CI/CD, branch protection, secret scanning")

    Rel(recruiter, copilot, "Uploads CVs, runs pipeline, triages queue", "HTTPS")
    Rel(manager, copilot, "Reviews shortlists, approves/rejects", "HTTPS")
    Rel(admin, copilot, "Manages platform, override, observability", "HTTPS")
    Rel(copilot, gemini, "LLM calls, embeddings", "HTTPS/REST")
    Rel(copilot, github, "CI runs on push", "HTTPS")
```

---

## C4 Level 2 — Container Diagram

```mermaid
C4Container
    title Container Diagram — Domain Copilot

    Person(user, "User (Recruiter / Manager / Admin)")

    Container(spa, "React SPA", "React + Vite + TypeScript + Tailwind", "Single-page app served by nginx. Role-based navigation and RBAC-aware UI.")
    Container(api, "FastAPI Backend", "Python 3.12 + FastAPI + SQLAlchemy", "REST API + SSE streaming. Clean Architecture: domain → application → infra → presentation.")
    Container(scheduler, "APScheduler", "APScheduler (in-process)", "Polls for SLA breaches every 5 min. Escalates overdue tasks.")
    ContainerDb(db, "PostgreSQL + pgvector", "PostgreSQL 16 + pgvector extension", "Relational + vector data. Stores candidates, jobs, review tasks, shortlists, audit logs, embeddings.")

    System_Ext(gemini, "Google Gemini API", "LLM + Embeddings")

    Rel(user, spa, "Uses", "HTTPS :3000")
    Rel(spa, api, "API calls + SSE", "HTTPS :8000 /api/v1/")
    Rel(api, db, "Reads/writes", "asyncpg + SQLAlchemy 2.0")
    Rel(api, gemini, "LLM calls + embeddings", "HTTPS SDK/REST")
    Rel(scheduler, db, "Reads tasks, writes escalations", "asyncpg")
```

---

## C4 Level 3 — Component Diagram (Backend)

```mermaid
C4Component
    title Component Diagram — FastAPI Backend

    Container_Boundary(api, "FastAPI Backend") {
        Component(routers, "Presentation Routers", "FastAPI routers", "auth, jobs, candidates, review_queue, chat, pipeline, reviewer_stats, observability, admin_*")
        Component(deps, "Dependencies", "FastAPI Depends", "JWT auth, RBAC enforcement, DI container injection")
        Component(usecases, "Use Cases", "Python async functions", "upload_candidate, run_screening_pipeline, triage_candidate, decide_candidate, ask_copilot, export_shortlist, compute_reviewer_stats, manage_sla_rules")
        Component(ports, "Ports", "Python Protocols", "LLMPort, EmbeddingPort, ReviewTaskRepositoryPort, DocumentRepositoryPort")
        Component(domain, "Domain", "Python dataclasses + Enums", "ReviewTask (state machine), Candidate, Job, SLARule, Shortlist, Evidence, BiasRules, Errors")
        Component(agents, "Agents + Orchestrator", "LangGraph", "evidence_extractor, bias_guard, rubric_scorer, shortlist_drafter, orchestrator (iteration breaker, per-step timeout, degrade path)")
        Component(infra_db, "DB Infrastructure", "SQLAlchemy + asyncpg", "ORM models, Alembic migrations, async session, pgvector raw SQL")
        Component(infra_llm, "LLM Infrastructure", "Gemini SDK + REST", "GeminiSdkAdapter, GeminiRestAdapter, FallbackPolicy, EmbeddingAdapter")
        Component(infra_retrieval, "Retrieval", "pgvector + tsvector", "Hybrid search: dense (cosine) + keyword (tsvector) + RRF fusion")
        Component(infra_obs, "Observability", "Python logging + structured", "TokenCostTracker, correlation IDs, per-agent traces")
    }

    Rel(routers, deps, "Uses for auth/DI")
    Rel(routers, usecases, "Calls")
    Rel(usecases, domain, "Operates on")
    Rel(usecases, ports, "Calls via ports")
    Rel(usecases, agents, "Invokes orchestrator")
    Rel(agents, ports, "Calls LLM/embedding ports")
    Rel(ports, infra_llm, "Implemented by")
    Rel(ports, infra_db, "Implemented by")
    Rel(agents, infra_retrieval, "Queries")
    Rel(usecases, infra_obs, "Logs traces")
```

---

## Sequence Diagram — Full Agentic Screening Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Recruiter
    participant FE as React SPA
    participant API as FastAPI
    participant Orch as Orchestrator (LangGraph)
    participant EE as evidence_extractor
    participant BG as bias_guard
    participant RS as rubric_scorer
    participant SD as shortlist_drafter
    participant DB as PostgreSQL
    participant LLM as Gemini API

    Recruiter->>FE: Upload CV (PDF)
    FE->>API: POST /candidates/upload
    API->>DB: Store candidate + chunks (pgvector)
    API->>LLM: embed(cv_text) → vector
    DB-->>API: candidate_id
    API-->>FE: {candidate_id, extracted_skills}
    FE-->>Recruiter: Skills shown

    Recruiter->>FE: Click "Run Screening"
    FE->>API: POST /pipeline/run {candidate_id, job_id}
    API->>DB: Create ReviewTask (PENDING_TRIAGE, SLA deadline set)
    API->>Orch: run_screening(state)
    Note over Orch: iteration_count=0, max=10, step_timeout=30s

    Orch->>EE: extract_evidence(cv_chunks, job_rubric)
    EE->>LLM: generate(system_prompt, cv_content)
    LLM-->>EE: structured evidence JSON
    EE-->>Orch: state{evidence=[...]}

    Orch->>BG: redact_protected_attributes(evidence)
    Note over BG: Deterministic regex — NO LLM
    BG->>DB: Write audit rows (what was redacted)
    BG-->>Orch: state{evidence=redacted, bias_redacted=true}

    Orch->>RS: score_rubric(evidence, job_criteria)
    RS->>LLM: generate(system_prompt, redacted_evidence) → justification only
    Note over RS: Numeric scores computed deterministically
    RS-->>Orch: state{rubric_scores={...}, shortlist_score=0.82}

    Orch->>SD: draft_shortlist(evidence, scores)
    SD->>LLM: generate(summary_prompt, evidence)
    LLM-->>SD: narrative summary
    SD-->>Orch: state{shortlist_draft="..."}

    Orch-->>API: screening complete
    API->>DB: Update ReviewTask (shortlist_draft stored)
    API-->>FE: SSE: {event: "complete", shortlist_draft: "..."}

    Note over Recruiter,DB: HUMAN GATE — Recruiter triages

    Recruiter->>FE: Forward to Manager (with reason)
    FE->>API: POST /review-queue/triage {action: forward_to_manager}
    API->>DB: ReviewTask.status → PENDING_MANAGER_REVIEW
    API->>DB: Write audit log entry
    API-->>FE: {status: PENDING_MANAGER_REVIEW}

    Note over Recruiter,DB: HUMAN GATE — Manager decides

    actor Manager
    Manager->>FE: Approve with comment
    FE->>API: POST /review-queue/decide {action: approve, reason: "..."}
    API->>DB: ReviewTask.status → APPROVED
    API->>SD: finalize_shortlist(shortlist_id) [GATED — only runs if APPROVED]
    SD->>DB: Mark shortlist as finalized
    API->>DB: Write audit log entry
    API-->>FE: {status: APPROVED}
```

---

## Data-Flow Diagram — Trust Boundaries

```mermaid
flowchart TB
    subgraph UNTRUSTED["🔴 Untrusted (User-supplied data)"]
        CV[CV / Job Description\nPDF / DOCX]
        Q[Copilot Chat Query]
    end

    subgraph BOUNDARY1["🟡 Input Boundary — Parsing & Validation"]
        PARSE[Document Parser\ntext extraction only]
        PYDANTIC[Pydantic input validation\nrequest body schemas]
    end

    subgraph TRUSTED_RETRIEVAL["🟢 Trusted Retrieval"]
        EMBED[Embedding\nGemini text-embedding-004]
        VEC[(pgvector index)]
        FTS[(PostgreSQL FTS)]
        RRF[RRF Fusion]
    end

    subgraph AGENT_BOUNDARY["🟡 Agent Boundary — LLM Trust Zone"]
        SYS[System Prompt\nINSTRUCTIONS — trusted]
        DOC_TAG["&lt;document&gt; tags\nuntrusted content clearly delimited"]
        BIAS[bias_guard\nDeterministic BEFORE LLM sees content]
        LLM_CALL[Gemini API call]
    end

    subgraph OUTPUT_BOUNDARY["🟡 Output Boundary — Validation"]
        PYDANTIC_OUT[Pydantic output validation]
        AUDIT[Audit trail write\nBias redaction log]
        DET_SCORE[Deterministic\nnumeric scoring]
    end

    subgraph HUMAN_GATE["🔐 Human Gate"]
        TRIAGE[HR Recruiter\ntriage decision]
        MANAGER[Hiring Manager\nfinal decision]
        ADMIN_OVR[Admin break-glass\naudit logged]
    end

    CV --> PARSE --> EMBED & BIAS
    Q --> PYDANTIC --> EMBED
    EMBED --> VEC & FTS --> RRF
    RRF --> DOC_TAG
    BIAS --> DOC_TAG
    SYS --> LLM_CALL
    DOC_TAG --> LLM_CALL
    LLM_CALL --> PYDANTIC_OUT --> DET_SCORE --> AUDIT
    AUDIT --> HUMAN_GATE

    style UNTRUSTED fill:#fee2e2,stroke:#ef4444
    style AGENT_BOUNDARY fill:#fef9c3,stroke:#eab308
    style BOUNDARY1 fill:#fef9c3,stroke:#eab308
    style OUTPUT_BOUNDARY fill:#fef9c3,stroke:#eab308
    style TRUSTED_RETRIEVAL fill:#dcfce7,stroke:#22c55e
    style HUMAN_GATE fill:#dbeafe,stroke:#3b82f6
```

---

## ER Diagram

```mermaid
erDiagram
    USER {
        uuid id PK
        string email UK
        string hashed_password
        string role "admin|hr_recruiter|hiring_manager"
        bool active
        datetime created_at
    }

    JOB {
        uuid id PK
        string title
        string description
        json skills "list[str]"
        datetime created_at
    }

    CANDIDATE {
        uuid id PK
        string full_name
        string email
        string sha256 UK "deduplication"
        string status "pending|screened|shortlisted|rejected"
        string priority "HIGH|MEDIUM|LOW"
        json extracted_skills
        datetime created_at
    }

    DOCUMENT_CHUNK {
        uuid id PK
        uuid candidate_id FK
        int chunk_index
        text content
        vector embedding "vector(768)"
        datetime created_at
    }

    REVIEW_TASK {
        uuid id PK
        uuid candidate_id FK
        uuid job_id FK
        string status "state machine"
        string priority "HIGH|MEDIUM|LOW"
        datetime triage_deadline_at
        datetime decision_deadline_at
        datetime triage_escalated_at
        datetime decision_escalated_at
        string triage_reason
        string manager_comment
        string admin_override_reason
        json audit_log "list of audit entries"
        datetime created_at
        datetime updated_at
    }

    SHORTLIST {
        uuid id PK
        uuid job_id FK
        string name
        string status "draft|finalized"
        json entries "list of ShortlistEntry"
        datetime created_at
    }

    SLA_RULE {
        uuid id PK
        uuid job_id FK "nullable = global rule"
        string priority "HIGH|MEDIUM|LOW"
        int triage_hours
        int decision_hours
        bool active
        uuid created_by FK
        datetime created_at
    }

    TOKEN_USAGE {
        uuid id PK
        string correlation_id
        string agent_name
        string model_name
        int input_tokens
        int output_tokens
        float estimated_cost_usd
        datetime created_at
    }

    USER ||--o{ SLA_RULE : "creates"
    JOB ||--o{ CANDIDATE : "has"
    JOB ||--o{ REVIEW_TASK : "has"
    JOB ||--o{ SHORTLIST : "has"
    JOB ||--o{ SLA_RULE : "overrides"
    CANDIDATE ||--o{ DOCUMENT_CHUNK : "has chunks"
    CANDIDATE ||--|| REVIEW_TASK : "has task"
```

---

## Layer Dependency Diagram

```mermaid
graph TD
    P["🌐 Presentation Layer\nFastAPI routers, middleware, OpenAPI\n(depends on Application)"]
    A["⚙️ Application Layer\nUse cases, Ports (interfaces)\n(depends on Domain only)"]
    I["🔧 Infrastructure Layer\nSQLAlchemy repos, Gemini adapters,\nRetrieval, Scheduler, Parser\n(implements Ports, depends on Domain)"]
    D["🏛️ Domain Layer\nEntities, State machines, Value objects,\nTyped errors\n(NO external dependencies)"]

    P --> A
    A --> D
    I --> D
    P -.->|"DI container injects\ninfra into application"| I

    style D fill:#dcfce7,stroke:#16a34a
    style A fill:#dbeafe,stroke:#2563eb
    style I fill:#fef9c3,stroke:#d97706
    style P fill:#f3e8ff,stroke:#7c3aed
```

---

## ADRs

See [`docs/adr/`](adr/) for all 4 Architecture Decision Records:

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-01](adr/ADR-01-chunking-strategy.md) | Paragraph-level chunks, 512 tokens, 50-token overlap | Accepted |
| [ADR-02](adr/ADR-02-pipeline-and-human-gate.md) | Human gate enforced at application layer, not agent layer | Accepted |
| [ADR-03](adr/ADR-03-two-stage-rbac-and-sla-rules.md) | Three roles (admin/recruiter/manager), two-level SLA resolution | Accepted |
| [ADR-04](adr/ADR-04-gemini-only-provider-fallback.md) | Two Gemini adapters (SDK + REST) as provider fallback | Accepted |
