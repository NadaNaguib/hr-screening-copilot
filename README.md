# Domain Copilot — HR Talent Screening Platform

> **Variant**: D6 (HR Talent Screening) + T5 (Human Review Queue as full product)
> ITI Dev Instructor Task — Nada Naguib

A production-quality **Agentic RAG** platform that assists HR teams in screening candidates while preserving human decision authority and providing a full bias audit trail.

**Demo Videos**:
- 🎬 Product demo (5–8 min): *(link pending — recording in progress)*
- 🎓 Teaching session (10 min): *(link pending — recording in progress)*

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 min)](#quick-start-5-min)
3. [Environment Variables](#environment-variables)
4. [Free API Keys](#free-api-keys)
5. [Running Without a Key (Local Model)](#running-without-a-key-local-model)
6. [Seeded Demo Accounts](#seeded-demo-accounts)
7. [5-Minute Demo Path](#5-minute-demo-path)
8. [Running Tests](#running-tests)
9. [Running the Evaluation Harness](#running-the-evaluation-harness)
10. [Repository Layout](#repository-layout)
11. [Documentation](#documentation)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Docker** ≥ 24.0 and **Docker Compose** ≥ 2.20
- **Git**
- A free Gemini API key (see [Free API Keys](#free-api-keys)) — optional; system degrades gracefully without one

That's it. No Python, Node, or Postgres needed locally.

---

## Quick Start (5 min)

```bash
git clone https://github.com/NadaNaguib/hr-screening-copilot.git
cd hr-screening-copilot
cp .env.example .env           # copy template
# Edit .env: paste your GEMINI_API_KEY (or leave blank to run in fallback mode)
docker compose up --build      # first run: ~2 min for image build
```

Wait for all services to show **healthy**:
```
✔ db        Started (healthy)
✔ migrate   Exited (0)
✔ api       Started (healthy)
✔ web       Started
```

Open **http://localhost:3000** and log in with a demo account.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Recommended | Gemini API key for LLM calls. Get free at https://aistudio.google.com |
| `JWT_SECRET` | **Yes** | Random string for signing JWTs. Generate: `openssl rand -hex 32` |
| `DATABASE_URL` | Auto-set | Set automatically by docker-compose. Override for external Postgres |
| `GEMINI_MODEL` | No | Model name (default: `gemini-1.5-flash`) |
| `GEMINI_EMBEDDING_MODEL` | No | Embedding model (default: `text-embedding-004`) |
| `SIMULATE_AGENT_FAILURE` | No | Set to `true` to force orchestrator degrade path (testing) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (default: `http://localhost:3000`) |

---

## Free API Keys

**Gemini (required for full functionality)**:
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API key"
3. Copy the key into `.env` as `GEMINI_API_KEY=your-key-here`
4. Free tier: 60 requests/minute, 1500 requests/day — sufficient for demo

---

## Running Without a Key (Local Model)

The system operates in **fallback mode** without a Gemini key:
- CV upload still works (regex-based skill extraction instead of LLM)
- Copilot Chat returns a graceful "AI unavailable" message
- Screening pipeline degrades to plain RAG (retrieval without agent reasoning)
- All RBAC, SLA, and review queue functionality works normally

To use a local Ollama model instead:
```bash
# 1. Run Ollama locally
ollama pull llama3.2

# 2. Point the adapter to Ollama (requires implementing OllamaAdapter — see ADR-04)
# Currently the system uses two Gemini adapters; Ollama support is planned
```

---

## Seeded Demo Accounts

These accounts are created by `scripts/seed.py` on first startup:

| Role | Email | Password | Can Do |
|------|-------|----------|--------|
| Admin | `admin@example.com` | `password123` | Everything, including user management, SLA rules, AI settings, break-glass override |
| HR Recruiter | `recruiter@example.com` | `password123` | Upload CVs, run pipeline, triage queue, set priority |
| Hiring Manager | `manager@example.com` | `password123` | Final approve/reject/edit decisions, export shortlist |

---

## 5-Minute Demo Path

**Step 1** — Log in as **HR Recruiter** (`recruiter@example.com` / `password123`)

**Step 2** — Create a job
- Click **Jobs & Candidates** → **New Job**
- Title: "Senior Python Engineer"
- Skills: `Python, FastAPI, PostgreSQL, Docker`
- Description: "Backend role requiring 3+ years of Python"

**Step 3** — Upload a CV
- Click **Upload CV** next to the job (or click **"Mimic CV & Match"** for instant candidate generation)
- Upload `Youssef_Eid_CV.pdf` (included in repo root)
- Observe extracted skills in the response

**Step 4** — Run the screening pipeline
- Click **Run Screening** on the uploaded candidate
- Watch the pipeline status in **Copilot Chat** or browser DevTools → Network → EventStream

**Step 5** — Ask the Copilot
- Navigate to **Copilot Chat**
- Ask: "Which candidate has the most Python experience?"
- Observe: grounded answer with citations to specific CV sections

**Step 6** — Ask an adversarial question (correct refusal)
- Ask: "Tell me the age and nationality of the candidates"
- Observe: system refuses to answer on protected attributes

**Step 7** — Triage as Recruiter
- Go to **Review Queue**
- Set priority to HIGH, add a reason, click **Forward to Manager**

**Step 8** — Decide as Hiring Manager
- Log out, log in as `manager@example.com` / `password123`
- Go to **Review Queue** → see the task with SLA countdown
- Click **Approve** with a comment

**Step 9** — Observe trace
- Log in as `admin@example.com` / `password123`
- Go to **Observability** → see token counts, cost, latency
- Go to **Reviewer Stats** → see approval rates, escalation count

---

## Running Tests

```bash
# Backend unit + integration tests
docker compose exec api pytest

# Or locally with venv:
cd hr-screening-copilot
source .venv/bin/activate   # or: python -m venv .venv && pip install -e ".[dev]"
pytest

# Frontend tests
cd frontend
npm install
npm test
```

---

## Running the Evaluation Harness

```bash
# With docker running:
docker compose exec api python -m eval.run_eval

# Locally:
source .venv/bin/activate
python eval/run_eval.py
```

The harness runs 25 Q/A pairs (including 10 adversarial cases) against the live system and prints:
- Per-question score (0.0 or 1.0)
- Average score
- Adversarial pass rate

Results are written to `docs/EVALUATION.md`.

---

## Repository Layout

```
.
├── src/copilot/           # Python backend (Clean Architecture)
│   ├── domain/            # Entities, value objects, state machines
│   ├── application/       # Use cases, ports
│   ├── infrastructure/    # DB, LLM adapters, retrieval, scheduler
│   ├── presentation/      # FastAPI routers
│   └── agents/            # LangGraph orchestrator + 4 agents
├── frontend/              # React + Vite + TypeScript + Tailwind + shadcn/ui
├── scripts/               # Seed script, synthetic corpus generator
├── eval/                  # Evaluation harness + golden Q/A set (25 pairs)
├── teaching/              # Teaching pack (slides, lab, answer key)
├── docs/                  # BRD, SYSTEM-DESIGN, ARCHITECTURE, SECURITY, EVALUATION, ADRs
├── Dockerfile             # Multi-stage Python image
├── docker-compose.yml     # db + migrate + api + web
└── .env.example           # Environment variable template
```

---

## Documentation

| Document | Description |
|---|---|
| [BRD](docs/BRD.md) | Business requirements, personas, traceability matrix |
| [System Design](docs/SYSTEM-DESIGN.md) | Target architecture (Part A) + MVP gap table (Part B) |
| [Architecture](docs/ARCHITECTURE.md) | C4 diagrams, sequence diagrams, ER, ADRs |
| [Security](docs/SECURITY.md) | OWASP Web + LLM Top 10 mapping |
| [Evaluation](docs/EVALUATION.md) | 25 golden Q/A results with adversarial analysis |
| [AI Usage Log](docs/AI-USAGE-LOG.md) | What was delegated to AI, mistakes caught, verification |
| [Project Status](docs/PROJECT_STATUS.md) | Living plan tracking all spec requirements |
| [Teaching Pack](teaching/) | Slides, lab, answer key, learning outcomes, common mistakes |

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: copilot` when running tests | Not using venv | `source .venv/bin/activate` then `pip install -e ".[dev]"` |
| Docker build fails on `hatchling` | README.md missing in builder stage | Already fixed: README.md is copied before build |
| Upload returns 500 | Gemini key missing or quota exceeded | Check `.env` key; system uses regex fallback automatically |
| Login returns 401 | Wrong password or seed not run | Confirm seed ran: `docker compose logs migrate` |
| pgvector embedding errors | Migration used wrong column type | Run `alembic upgrade head` to apply latest migration |
| Chat returns empty | Vector index empty | Upload at least one CV and run the pipeline first |
| SLA timer shows `—` | Task was created without SLA rules set | Create SLA rules in Admin → SLA Settings |

