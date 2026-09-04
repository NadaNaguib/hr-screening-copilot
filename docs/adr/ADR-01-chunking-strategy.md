# ADR-01: Chunking Strategy

## Status
Accepted

## Context
We need to split CVs and job descriptions into retrieval chunks that preserve semantic coherence.

## Decision
Use paragraph-level chunks with 50-token overlap, capped at 512 tokens. Metadata includes source document, page, and candidate/job id.

## Consequences
- Preserves sentence/paragraph context better than fixed-size chunks.
- Overlap reduces boundary truncation.
- Slightly larger index than pure fixed chunks.
