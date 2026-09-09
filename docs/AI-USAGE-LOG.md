# AI Usage Log

> Required by the ITI task spec. Maintained honestly per the instruction:
> "Catching model errors is exactly the skill we need you to teach."

---

## What Was Delegated to AI

| Task | Tool/Model | What AI Did | Verification |
|------|-----------|-------------|--------------|
| Boilerplate FastAPI router scaffolding | Antigravity (Gemini) | Generated initial router structure with type hints | Manually reviewed every route, corrected RBAC decorators |
| LangGraph orchestrator skeleton | Antigravity | Generated graph node structure | Rewrote state typing, corrected edge conditions |
| Alembic migration | Antigravity | Generated column definitions | Verified column types against domain models; caught `Vector(768)` vs `double precision[]` mismatch |
| React component scaffolding | Antigravity | Generated Tailwind component skeletons | Rewrote all business logic, state management, and API calls |
| Teaching slides content | Antigravity | Generated slide structure and code examples | Verified all code examples compile and run; corrected mermaid syntax |
| Evaluation golden set | Antigravity | Generated initial Q/A pairs | Added all adversarial cases manually; verified expected answers match system behavior |
| OWASP LLM Top 10 mapping table | Antigravity | Generated initial mapping | Cross-referenced with actual OWASP documentation; corrected two incorrectly categorised items |

---

## What Was Written Without AI

| Component | Rationale |
|-----------|-----------|
| Domain state machine (`review_task.py`) | Core business logic — required precise understanding of role-action-transition matrix |
| Bias guard regex patterns | Needed domain knowledge of protected attributes in Egyptian labour law context |
| SLA resolution logic (`resolve_sla_deadline.py`) | Two-level precedence rules required careful reasoning |
| RBAC enforcement in use cases | Security-critical — checked line by line |
| pgvector raw SQL chunk insertion | Debugged after ORM failed; required understanding of asyncpg type casting |
| All git commit messages | Written to follow conventional commits spec |
| This AI usage log | Written honestly from memory |

---

## Where AI Misled Me (and How I Caught It)

### Mistake 1: Alembic Migration — Vector Column Type
**What AI generated**: `Column(Vector(768))` in the ORM and a standard `CREATE TABLE` migration.  
**What was wrong**: asyncpg doesn't natively handle the pgvector `vector` type — it serialised embeddings as strings. The migration created `double precision[]` not `vector(768)`.  
**How caught**: Upload pipeline failed with `psycopg2.ProgrammingError: column "embedding" is of type double precision[] but expression is of type text`.  
**Fix**: Manually altered the column to `vector(768)` and rewrote chunk insertion as raw SQL with explicit `::vector` cast.  
**Lesson**: Never trust AI-generated database migrations for non-standard column types. Always test with real data.

### Mistake 2: bcrypt Password Truncation
**What AI generated**: Standard `bcrypt.hashpw(password.encode(), salt)`.  
**What was wrong**: bcrypt silently truncates passwords at 72 bytes. Long passwords were accepted as valid even when wrong.  
**How caught**: Integration test with a 100-character password passed when it should have failed.  
**Fix**: Added explicit `password[:72].encode()` before hashing, with a warning comment.  
**Lesson**: Security libraries have non-obvious truncation behaviours. Read the full docs, not just the quick-start.

### Mistake 3: FastAPI Async Session Not Auto-Committing
**What AI generated**: `async with async_session() as session: yield session` — standard pattern.  
**What was wrong**: FastAPI's `Depends` with `async with` does NOT auto-commit on success — only rolls back on exception. Write operations were silently discarded.  
**How caught**: Priority updates returned 200 but changes were not persisted. Discovered via manual testing.  
**Fix**: Added explicit `await session.commit()` after the endpoint `yield` and `await session.rollback()` on exception.  
**Lesson**: "Standard patterns" from documentation may omit critical details for async contexts. Always verify writes are actually committed.

### Mistake 5: SQLAlchemy MissingGreenlet on Lazy Relationships
**What AI generated**: `rubric.criteria` accessed directly in `_rubric_to_domain()` without eager loading.  
**What was wrong**: In asyncpg, accessing unloaded SQLAlchemy relationship attributes outside of an eager load context raises `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been spawned`.  
**How caught**: "Run Pipeline" endpoint returned 500 Internal Server Error when evaluating rubrics.  
**Fix**: Added `options(selectinload(RubricORM.criteria))` to query and safely extracted criteria via `orm.__dict__.get("criteria", [])`.  
**Lesson**: Async SQLAlchemy requires explicit eager loading strategy (`selectinload` or `joinedload`) for all relationships accessed in domain converters.

### Mistake 6: LangGraph Dict vs. Object State Access
**What AI generated**: `final_state.degraded` on the returned state from `graph.ainvoke()`.  
**What was wrong**: LangGraph state returns a Python `dict`, not a Pydantic object instance. Accessing `.degraded` triggered `AttributeError: 'dict' object has no attribute 'degraded'`.  
**How caught**: Pipeline execution crashed at the completion step when assembling the final response.  
**Fix**: Changed access to `final_state.get("degraded", False)` and dict-safe retrieval.  
**Lesson**: Verify the runtime return type of orchestrator graphs; LangGraph channels serialize into dictionaries at execution boundaries.

### Mistake 7: Strict Case-Sensitive Enum Deserialization
**What AI generated**: `Priority(value)` directly parsing priority query parameters and JSON payloads.  
**What was wrong**: Frontend and database conventions vary (`HIGH` vs `high`). Passing uppercase `"HIGH"` raised `'HIGH' is not a valid Priority`.  
**How caught**: Navigating to the SLA settings tab threw consecutive exceptions on valid uppercase priority strings.  
**Fix**: Added case-insensitive `Priority.from_str()` class method normalizing input strings to lowercase before enum lookup.  
**Lesson**: Always implement resilient, case-insensitive string parsing for domain enums exposed at boundary APIs.

---

## AI Error Rate Estimate
- ~40% of AI-generated code required significant correction before use
- ~20% required minor fixes (type annotations, imports)  
- ~40% was usable as scaffolding with business logic added
- 0% was committed verbatim without review

