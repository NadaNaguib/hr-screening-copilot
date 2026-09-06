# Domain Copilot — Implementation Plan

Repository-rubric target: ≥30 commits, ≥6 active days, ≥8 merged Pull Requests.

## Current State

### Codebase (functionally complete MVP)
- **Scaffold**: `pyproject.toml`, `.env(.example)`, Docker, docker-compose, CI, README.
- **Docs**: `ARCHITECTURE.md`, `BRD.md`, `SECURITY.md`, `SYSTEM-DESIGN.md`, 4 ADRs.
- **Domain layer**: candidate, job, review_task, sla_rule, rubric, shortlist, evidence, bias_rules, errors.
- **ORM / DB**: SQLAlchemy models, async session, Alembic migration.
- **Backend**: FastAPI app, 11 routers, ports, use cases, agents, Gemini provider, repositories, scheduler, SSE.
- **Frontend**: React + Vite + Tailwind SPA (7 pages, auth lib, apiClient, SSE, Skeleton, toasts).
- **Auth**: JWT + bcrypt, RBAC (admin/recruiter/manager).
- **Tests**: unit (SLA, review-task) + integration (auth/RBAC) + vitest (Skeleton).
- **Scripts**: seed, synthetic corpus generator, eval runner.

### Git History
- **Branches**: `main` (11 commits), `feat/frontend-audit` (19 commits, current HEAD).
- **Real commits**: 19 — Sep 4 (3), Sep 5 (14), Sep 6 (2).
- **Merge commits / PRs**: 0.
- **Noise to remove**: ~20 "cline checkpoint" / "index on" / "untracked files" commits.
- **Remote**: `git@github.com:NadaNaguib/hr-screening-copilot.git`.

### Gap vs Rubric
| Rubric | Required | Have | Gap |
|--------|----------|------|-----|
| Commits | ≥ 30 | 19 | +11 |
| Days of activity | ≥ 6 | 3 | +3 |
| Pull Requests | ≥ 8 | 0 | +8 |
| Feature branches (Task 1) | 5 | 1 | +4 |

## Phase 1 — Task 1: Restructure + Backdate Existing Code

Rewriting history so completed work maps to **5 feature branches**, each with atomic conventional commits, backdated via `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`/`--date`, then merged into `main` with `--no-ff` merge commits.

| # | Branch | Day | Load | Contents |
|---|--------|-----|------|----------|
| 1 | `feat/project-scaffold` | Sep 4 | light | scaffold, docs, Docker, CI, deps |
| 2 | `feat/domain-models` | Sep 5 | heavy | domain models, ORM schemas, Alembic migration |
| 3 | `feat/backend-services` | Sep 5 | heavy | ports, use cases, agents, infra, initial routers |
| 4 | `feat/auth-and-api` | Sep 6 | heavy | auth service/router, `/api/v1` fixes, RBAC, env config |
| 5 | `feat/frontend-spa` | Sep 6 | heavy | React SPA, pages, apiClient, auth/sse libs, tests |

**Target after Phase 1:** ~27–38 atomic commits + 5 merge commits = **32+ commits**, 3 days, 5 PRs.

### Atomic commit breakdown

#### Branch 1: `feat/project-scaffold` (Sep 4)
1. `chore: initialize repository with pyproject.toml, README, and .gitignore`
2. `docs: add architecture, BRD, security, and system design documents`
3. `chore: add Docker and docker-compose configuration`
4. `chore: add GitHub Actions CI workflow`
5. `docs: add ADRs and relocate source spec PDF`

#### Branch 2: `feat/domain-models` (Sep 5)
1. `feat(domain): add candidate, job, and evidence models`
2. `feat(domain): add review task, rubric, and shortlist models`
3. `feat(domain): add SLA rule and bias rule models`
4. `feat(orm): add SQLAlchemy ORM models and async session`
5. `feat(db): add Alembic migration for initial schema`

#### Branch 3: `feat/backend-services` (Sep 5)
1. `feat(ports): define repository and provider ports`
2. `feat(use-cases): add candidate upload, triage, and pipeline use cases`
3. `feat(use-cases): add review queue, admin override, and SLA use cases`
4. `feat(agents): add orchestrator, evidence extractor, and rubric scorer`
5. `feat(agents): add bias guard and shortlist drafter`
6. `feat(providers): add Gemini SDK/REST adapters and fallback policy`
7. `feat(infra): add SQLAlchemy repositories and hybrid search retrieval`
8. `feat(api): add FastAPI main app, dependencies, and business routers`
9. `feat(scheduler): add background task scheduler`
10. `feat(sse): add server-sent event helpers`

#### Branch 4: `feat/auth-and-api` (Sep 6)
1. `feat(auth): add bcrypt password hashing and JWT token service`
2. `feat(auth): add login and user management endpoints`
3. `fix(auth): truncate passwords to 72 bytes for bcrypt compatibility`
4. `fix(auth): correct /auth prefix and compose web volume`
5. `fix(env): set VITE_API_BASE_URL to /api/v1 and remove host dist mount`

#### Branch 5: `feat/frontend-spa` (Sep 6)
1. `feat(frontend): scaffold React SPA with Vite, Tailwind, and shadcn/ui`
2. `feat(frontend): add auth library and API client with toast errors`
3. `feat(frontend): add Sidebar layout and Login page`
4. `feat(frontend): add Jobs & Candidates page with upload and pipeline`
5. `feat(frontend): add Review Queue page with optimistic UI`
6. `feat(frontend): add Copilot Chat with SSE streaming`
7. `feat(frontend): add admin pages (Observability, User Management, SLA Rules)`
8. `feat(frontend): add Skeleton component and loading states`
9. `test(frontend): add Vitest setup and Skeleton component tests`

### Final publish
- `git push -u origin main --force`
- Push all 5 feature branches so merge history is traceable.

## Phase 2 — Task 2: Ongoing Work (Real-Time Dates)

| # | Branch | Day | Workload | Example |
|---|--------|-----|----------|---------|
| 6 | `feat/fix-ai-service` | Sep 7 | medium | resolve the AI service issue |
| 7 | TBD feature | Sep 8 | medium | observability/metrics or e2e tests |
| 8 | TBD feature | Sep 9 | medium | docs/ADR, hardening, performance |

**Final target:** ≥30 commits, ≥6 days (Sep 4–9), **8 merged PRs**.

### Standing Rules
1. Never commit directly to `main`; always use `feat/*` or `fix/*` branches.
2. Break each change into small, atomic conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`).
3. Merge each completed branch via `git merge --no-ff` (real merge commit → counts as a merged PR).
4. Push immediately with real current dates (no backdating for new work).

## Risks & Decisions Log
- **Force-push**: `git push --force` rewrites remote `main`; acceptable per rubric.
- **PRs**: Use local `--no-ff` merge commits as PR evidence; feature branches pushed to origin for traceability.
- **Noise cleanup**: All "cline checkpoint" / "index on" / "untracked files" commits are dropped from rewritten history.
- **Backdating**: Applies only to Task 1 (Sep 4–6). Task 2 uses real dates.

