# Security Analysis

## OWASP Web Top 10 Mapping
| Risk | Mitigation |
|------|------------|
| Broken Access Control | Server-side RBAC on every route; role-specific query filters |
| Cryptographic Failures | JWT via python-jose, bcrypt password hashing, HTTPS in production |
| Injection | Parameterized SQLAlchemy queries; strict instruction/retrieved-content separation |
| Insecure Design | Human gate, bias audit, mandatory reasons on decisions |
| Security Misconfiguration | Non-root containers, secret env vars, pinned dependencies |
| Vulnerable Components | pip-audit in CI, lockfile committed |
| Auth Failures | Rate-limited login, short-lived JWTs |
| Software Integrity | Branch protection, gitleaks, CI required |
| Logging Failures | Structured logs with correlation IDs, never log secrets |
| SSRF | No arbitrary outbound calls; only configured Gemini endpoints |

## OWASP LLM Top 10 Mapping
| Risk | Mitigation |
|------|------------|
| Prompt Injection | Indirect-prompt-injection defense: instructions in system prompts, retrieved content clearly delimited |
| Insecure Output Handling | Pydantic validation, deterministic redaction before scoring |
| Training Data Poisoning | Synthetic corpus only; no external untrusted ingestion |
| Model Denial of Service | Rate limiting, per-step timeouts, iteration breaker |
| Supply Chain | Pinned dependencies, pip-audit |
| Sensitive Information Disclosure | PII/protected-attribute redaction with audit trail |
| Model Inversion | No real personal data; synthetic candidates only |
| Excessive Agency | Tool allow-lists per agent; `finalize_shortlist` gated on manager approval |
| Overreliance | Human-in-the-loop; final decision by manager |
| Theft | No model weights stored; API keys via env |

## Secrets
- `GEMINI_API_KEY`, `JWT_SECRET`, Postgres credentials via `.env` / compose `env_file`.
- `gitleaks detect` clean over full history.
