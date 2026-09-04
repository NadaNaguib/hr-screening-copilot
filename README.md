# Domain Copilot — HR Talent Screening Platform

A production-quality Agentic RAG platform for HR talent screening, built for the ITI Dev Instructor task (variant D6 + T5 human-review queue).

## 5-minute demo

```bash
cp .env.example .env          # fill in GEMINI_API_KEY and JWT_SECRET
docker compose up --build     # wait for the healthchecks to turn green
```

Open http://localhost:3000 and log in with one of the demo accounts created by the seed script (see `scripts/seed.py` output).

## Repository layout

- `src/copilot/` — Python backend (Clean Architecture: domain → application → infrastructure → presentation)
- `frontend/` — React + Vite + TypeScript + Tailwind + shadcn/ui
- `scripts/` — synthetic corpus generation and database seeding
- `eval/` — evaluation harness and golden Q/A set
- `docs/` — BRD, SYSTEM-DESIGN, ARCHITECTURE, ADRs, SECURITY, EVALUATION

## Documentation

- [Business Requirements](docs/BRD.md)
- [System Design](docs/SYSTEM-DESIGN.md)
- [Architecture & C4 diagrams](docs/ARCHITECTURE.md)
- [Security analysis](docs/SECURITY.md)
- [Evaluation results](docs/EVALUATION.md)

## Roles

- **Admin** — user management, observability, SLA rules, break-glass override
- **HR Recruiter** — ingestion, triage, advanced queue
- **Hiring Manager** — final decision queue, shortlist export

## License

MIT
