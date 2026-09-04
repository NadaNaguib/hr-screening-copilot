# ADR-02: Pipeline and Human Gate

## Status
Accepted

## Context
The system must balance autonomous agentic screening with accountable human decisions.

## Decision
Agents produce evidence, bias-redacted scores, and a draft shortlist, but the actual state transition that triggers the gated `finalize_shortlist` tool is only permitted after a Hiring Manager `approve` or `edit_and_approve` decision.

## Consequences
- Managers retain final authority.
- Recruiter forward alone does not finalize a shortlist.
- Audit trail captures every gate transition.
