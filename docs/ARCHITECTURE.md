# Architecture

## C4 Context Diagram

```text
[HR Recruiter] ----> [Domain Copilot Web App]
[Hiring Manager] ---> [Domain Copilot Web App]
[Admin] ------------> [Domain Copilot Web App]

[Domain Copilot Web App] ----> [Gemini LLM]
[Domain Copilot Web App] ----> [Postgres + pgvector]
```

## C4 Container Diagram

- Web Browser loads React SPA served by nginx.
- nginx reverse-proxies `/api/*` to FastAPI.
- FastAPI uses application use cases and infrastructure adapters.
- SQLAlchemy + asyncpg talk to Postgres.
- APScheduler monitors SLA breaches.

## Clean Architecture Layers

- `domain/`: entities, value objects, state machines, typed errors. No framework imports.
- `application/ports/`: interfaces for external concerns.
- `application/use_cases/`: business operations, orchestrated by presentation routers.
- `infrastructure/`: concrete implementations of ports.
- `presentation/`: FastAPI routes, middleware, OpenAPI docs.

See ADRs in `docs/adr/` for detailed design decisions.
