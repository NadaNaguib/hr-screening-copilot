# Business Requirements Document (BRD)

## Purpose
Build an Agentic RAG platform that assists HR in screening candidates while preserving human decision authority and enabling bias audit.

## Stakeholders
- HR Recruiter (triage)
- Hiring Manager (final decision)
- Admin (break-glass override, observability, SLA rules)

## Functional Requirements
1. **Document ingestion**: upload CVs and job descriptions (PDF/DOCX), deduplicate by SHA-256, parse text.
2. **Agentic screening pipeline**: evidence extraction, bias-guard redaction, rubric scoring, shortlist drafting.
3. **Two-stage review**: HR Recruiter triages, Hiring Manager decides, admin override only as break-glass.
4. **SLA rules**: configurable global defaults + per-job overrides, auto-escalation on breach.
5. **Human review queue**: role-filtered views, search/filter, audit trail.
6. **Copilot chat**: streaming answers grounded in retrieved evidence with citations.
7. **Export**: shortlist PDF/CSV after manager approval.
8. **Observability**: token/cost accounting, LLM traces, correlation IDs.
9. **Security**: RBAC, input validation, indirect-prompt-injection defense, PII redaction audit.
10. **Evaluation**: ≥25 golden Q/A including adversarial, reported in EVALUATION.md.

## Non-functional Requirements
- Clean Architecture; domain/application independent of frameworks.
- Docker single-command deployment.
- CI green: ruff, mypy, pytest, pip-audit, gitleaks.
- ≥30 commits, ≥8 PRs, branch protection.

## Backlog
- Teaching pack (slides/lab/answer key)
- 2 demo videos
