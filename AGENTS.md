# NammaNexus AI — Agent Instructions

## 1. Project Overview

NammaNexus AI is an AI-powered civic intelligence platform for Bengaluru.

The project is being developed as a final-year college project and portfolio project.

The immediate goal is to build a working, demonstrable, deployable-quality product locally first, then deploy stable milestones as the project progresses.

The project is NOT a greenfield project. Existing code, database migrations, architecture, and working functionality must be preserved unless there is a justified reason to change them.

---

## 2. Core Development Principle

DO NOT blindly vibe-code.

Before modifying the codebase:

1. Inspect the existing implementation.
2. Understand the relevant architecture.
3. Identify the minimum files that need to change.
4. Explain the proposed approach.
5. Preserve existing working behavior.
6. Implement only the required change.
7. Run relevant tests.
8. Review the resulting changes.
9. Explain important implementation decisions.

Do not rewrite working code unnecessarily.

---

## 3. Project Pillars

NammaNexus AI contains five major pillars:

1. SpotFix AI
2. NammaServe AI
3. CivicVoice AI
4. SafeStreet AI
5. CivicAssist AI

These pillars should share common platform infrastructure while keeping their domain logic modular.

Do not create five unrelated applications.

---

## 4. Technology Stack

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Framer Motion
- TanStack Query

### Backend

- Python
- FastAPI
- Pydantic
- Pydantic Settings
- SQLAlchemy
- Alembic
- Psycopg

### Database

- PostgreSQL
- Supabase PostgreSQL
- PostGIS

### Authentication

- Supabase Auth

### AI

- Gemini Vision where image understanding is required
- Groq-hosted LLMs for appropriate text tasks

### Testing

- Pytest

---

## 5. Existing Backend Foundation

The backend already contains:

- FastAPI
- SQLAlchemy
- PostgreSQL/Supabase
- PostGIS
- Alembic
- Psycopg
- Pytest
- Pillow
- Local storage support

The existing complaints table was created by:

`e70b7b3f7c2c_create_complaints_table.py`

Revision:

`e70b7b3f7c2c`

This migration has already been applied.

### IMPORTANT

Never recreate the initial complaints migration.

Never delete or rewrite the existing migration simply to make a new feature easier.

Database schema changes must use new Alembic migrations.

---

## 6. Current Complaint Foundation

The existing Complaint model contains:

- id
- status
- category
- description
- latitude
- longitude
- image_storage_key
- created_at
- updated_at

This is the existing foundation and must be evolved carefully.

Do not assume the final Complaint schema is already complete.

---

## 7. Database Rules

Use:

Model change
→ Alembic migration
→ Review migration
→ Apply migration
→ Verify database

Do not make manual production schema changes when an Alembic migration is appropriate.

Use PostGIS for geographic operations.

Do not ask an LLM to determine:

- Ward
- Geographic containment
- Distance
- Coordinates
- Spatial relationships

These must be handled deterministically.

---

## 8. Architecture Rules

Prefer clear separation of responsibilities.

Typical backend structure:

API/router
↓
Service/domain logic
↓
Database/repository or data access
↓
External services where required

Keep FastAPI routers relatively thin.

Do not put the entire business workflow inside route functions.

Shared services should be reused where appropriate.

Avoid duplicate:

- Database configuration
- Authentication logic
- Storage logic
- AI configuration
- Location logic
- Communication logic
- Logging
- Security utilities

---

## 9. AI Rules

AI is not the source of truth.

Use deterministic systems for:

- Authentication
- Authorization
- Database operations
- Geographic calculations
- Ward lookup
- Authority lookup
- Business rules
- Status transitions
- Permissions

Use AI where it provides meaningful value, such as:

- Image understanding
- Classification
- Natural-language understanding
- Summarization
- Theme extraction
- Complaint drafting
- Evidence-grounded explanation

AI output must be validated before being used by application logic.

Never blindly trust LLM output.

---

## 10. Human Approval

High-impact external actions require explicit human/user approval where specified by the product architecture.

Examples:

AI complaint draft
→ Citizen review
→ Citizen approval
→ Communication

AI-generated content must not silently be sent externally.

CivicAssist must never bypass approval workflows belonging to specialized pillars.

---

## 11. Security

Never:

- Hardcode API keys
- Commit secrets
- Modify `.env` without explicit instruction
- Expose secrets to the frontend
- Trust client-provided ownership/user IDs
- Trust LLM output as authorization
- Allow natural language to bypass permissions
- Log secrets
- Expose internal stack traces to users

Use:

- Environment variables
- Authentication
- Authorization
- Input validation
- Secure file handling
- File size/type validation
- Safe error responses
- Appropriate access control

Treat user location and uploaded images as potentially sensitive information.

---

## 12. File Changes

Before changing a file:

- Determine whether it is actually necessary.
- Preserve existing interfaces unless there is a justified reason to change them.
- Avoid unrelated refactoring.
- Avoid duplicate utilities/services.

When creating a new file, the implementation should have a clear architectural purpose.

---

## 13. Dependencies

Do not install packages automatically just because they might be useful.

Before adding a dependency:

1. Determine whether the existing stack can solve the problem.
2. Explain why the dependency is required.
3. Check whether it introduces unnecessary complexity.
4. Add it only when justified.

---

## 14. Testing

New functionality should have appropriate tests.

Prefer:

- Unit tests for isolated business logic
- Integration tests for database/PostGIS behavior
- API tests for endpoints
- Mocked AI/external services where appropriate

Do not make the entire test suite dependent on live AI APIs or external APIs.

Tests should be deterministic whenever possible.

---

## 15. Git Safety

Before significant changes:

Check:

`git status`

After implementation:

Check:

`git diff`

Review changes before committing.

Prefer meaningful commits such as:

- `feat: add image validation`
- `feat: add ward resolution`
- `test: add complaint service tests`
- `fix: handle invalid coordinates`

Do not create giant meaningless commits.

---

## 16. Secrets

Never read, print, expose, or modify secret values unnecessarily.

`.env` contains sensitive configuration.

Do not include secret values in:

- Responses
- Logs
- Documentation
- Git commits
- Test output
- Screenshots

If `.env` values are needed, inspect only variable names or configuration structure unless the actual secret is explicitly required.

---

## 17. SpotFix Rules

SpotFix supports civic issues including:

- Pothole
- Garbage/waste
- Water leakage
- Drainage/waterlogging
- Broken street light
- Fallen tree

SpotFix architecture should follow:

Citizen input
→ validation
→ image processing
→ AI analysis
→ structured validation
→ deterministic location/ward resolution
→ authority resolution
→ complaint drafting
→ citizen review
→ approval
→ communication

The original citizen image must be preserved.

AI must not generate a replacement image for external communication.

---

## 18. PostGIS Rules

Geospatial truth must come from PostGIS or another deterministic geospatial service.

Never use an LLM to decide:

"Which ward is this?"

Instead:

Coordinates
→ PostGIS
→ Ward
→ Authority mapping

Spatial queries should use appropriate indexes and geographic filtering.

---

## 19. External APIs

Do not assume an external API is available.

Before integrating an external service:

- Verify API availability.
- Verify authentication requirements.
- Verify rate limits.
- Verify terms of service.
- Verify licensing/data usage restrictions.
- Verify whether the intended use is permitted.

Do not build critical architecture around an inaccessible or unauthorized data source.

---

## 20. RAG

Do not automatically introduce vector databases.

Use normal database queries for structured data such as:

- Distance
- Category
- Price
- Rating
- Dates
- Status
- Counts
- Geographic filtering

Use semantic/vector retrieval only where it provides real value.

`pgvector` is optional and must be justified by the actual use case.

---

## 21. Performance

Prefer:

- Async I/O where appropriate
- Parallel independent operations
- Efficient database queries
- Spatial indexes
- Pagination
- Caching where useful
- Background processing for long-running work
- Timeouts
- Avoiding duplicate AI calls

Do not optimize prematurely without evidence.

Do not add unnecessary infrastructure.

---

## 22. Error Handling

Expected failures should be handled explicitly.

Examples:

- Invalid input
- Invalid image
- AI unavailable
- AI timeout
- Malformed AI output
- Database failure
- External API failure
- Missing geographic coverage
- Missing authority mapping
- Storage failure

Users should receive safe, useful messages.

Technical details should be logged internally where appropriate.

---

## 23. Agent Workflow

When implementing a significant task:

1. Inspect existing code.
2. Explain the plan.
3. Identify files involved.
4. Implement the smallest appropriate change.
5. Run relevant tests.
6. Inspect failures.
7. Fix failures.
8. Run tests again.
9. Review the final diff.
10. Report exactly what changed.

Do not modify unrelated files.

---

## 24. Agent Permissions

Do not perform destructive actions without explicit approval.

Examples requiring caution:

- Deleting files
- Rewriting migrations
- Dropping database tables
- Resetting databases
- Removing existing functionality
- Changing authentication architecture
- Modifying secrets
- Installing major dependencies
- Large-scale refactoring

---

## 25. Documentation

Important architecture decisions should be documented.

Useful documentation may include:

- `docs/architecture.md`
- `docs/database.md`
- `docs/ai-architecture.md`
- `docs/security.md`
- `docs/deployment.md`
- `docs/decisions/`

Do not create documentation that does not provide useful project value.

Documentation should reflect the actual implementation.

---

## 26. Learning Requirement

The developer is learning backend and AI engineering.

Do not hide important concepts behind generated code.

For significant changes, explain:

- What is being built
- Why it is needed
- Where it fits
- How data flows
- Important design decisions
- Important code
- How it is tested

Large repetitive implementation may be generated by an agent, but the developer should understand the important architecture and logic.

---

## 27. Current Development Strategy

The project is being developed locally first.

The immediate objective is to complete stable pillar functionality and demonstrate the product locally.

Deployment will happen after appropriate milestones rather than forcing deployment before the product is ready.

Code should nevertheless be structured so that deployment can be introduced without rewriting the system.

---

## 28. Final Rule

Before making changes, ask:

1. Does this already exist?
2. Is this change actually necessary?
3. Which architectural layer owns this responsibility?
4. Does this affect the database?
5. Does it require an Alembic migration?
6. Does it introduce a security risk?
7. Does it introduce unnecessary AI usage?
8. Does it require a new dependency?
9. How will it be tested?
10. Does it affect another pillar?

When uncertain, stop and ask rather than guessing.