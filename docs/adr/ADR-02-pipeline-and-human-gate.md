# ADR-02: Pipeline and Human Gate

## Status
Accepted

## Context
The system must balance autonomous agentic screening with accountable human decisions.

## Decision
Agents produce evidence, bias-redacted scores, and tailored interview questions, but the candidate's Review Task never transitions to `APPROVED` (or `EDITED_AND_APPROVED`), and no shortlist/export record is created, without a Hiring Manager `approve` or `edit_and_approve` decision.

## Consequences
- Managers retain final authority.
- Recruiter forward alone does not finalize a shortlist or export a candidate.
- Audit trail captures every gate transition.
