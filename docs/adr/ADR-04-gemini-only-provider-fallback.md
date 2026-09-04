# ADR-04: Gemini-Only Provider Fallback

## Status
Accepted

## Context
The task requires ≥2 provider implementations and a fallback chain. We have only one available key provider (Gemini).

## Decision
Implement two distinct Gemini adapters: `GeminiSdkAdapter` (uses `google-generativeai`) and `GeminiRestAdapter` (direct HTTP to the Gemini REST API). The fallback chain is SDK → REST → graceful degrade. The `LLMPort` interface is vendor-neutral so a future OpenAI/Anthropic adapter can be dropped in without changing domain/application code.

## Consequences
- Satisfies the literal requirement of two concrete implementations.
- Single-provider risk remains; documented as a tradeoff.
- Port abstraction keeps the system open for multi-vendor future.
