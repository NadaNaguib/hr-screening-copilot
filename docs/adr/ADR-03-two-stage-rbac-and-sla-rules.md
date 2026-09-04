# ADR-03: Two-Stage RBAC and SLA Rules

## Status
Accepted

## Context
HR screening naturally separates initial triage from final hiring authority. The platform must enforce this separation while remaining flexible on SLA timing.

## Decision
- Exactly three roles: `admin`, `hiring_manager`, `hr_recruiter`.
- Recruiter triages; manager decides; admin override is break-glass only and logged as `ADMIN_OVERRIDE`.
- SLA rules resolve at two levels: job-specific override → global default.

## Consequences
- Clear separation of duties supports bias audit.
- Simplified SLA model avoids team/department complexity.
- Admin override visibility discourages routine use.
