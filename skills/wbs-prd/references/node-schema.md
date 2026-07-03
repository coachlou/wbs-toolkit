# WBS Node Schema

Every node at every level uses this exact structure. The tree is self-similar.

## Field reference

```yaml
id: string          # UPPER-KEBAB-CASE. Convention: DOMAIN-FEATURE-UNIT
                    # ROOT is always ROOT. CAP nodes: CAP-{DOMAIN}. See SKILL.md for full table.

type: string        # One of: product | capability | feature | module | work_package | task | step
                    # Decompose to work_package in the initial tree. task/step added at execution.

title: string       # Short imperative phrase: "Build magic-link endpoint"

objective: string   # One sentence: what this delivers and why it matters to the parent's goal

status: string      # Always 'pending' on generation. wbs.py manages transitions.
                    # Valid: pending | ready | in_progress | complete | blocked | decomposed

inputs:             # List of strings: data, artifacts, or conditions this node needs to start
  - string

constraints:        # List of strings: functional rules this node must obey
  - string          # e.g. "stateless API", "15-minute token expiry", "WCAG AA compliance"
                    # NOT tech stack — that belongs in .wbs/context.md

outputs:            # List of strings: concrete deliverables (files, endpoints, schemas, test suites)
  - string

acceptance_criteria: # List of strings: verifiable conditions that prove this node is done
  - string           # Must be testable without asking the author. At least one per node.

verify:              # Shell commands `wbs.py done` runs — all must exit 0 or completion is refused
  - string           # One per leaf: the command that runs this node's tests

dependencies:        # Nodes that must reach 'complete' before this node is executable
  - id: string       # Must match an id that exists elsewhere in the tree
    type: string     # data     — needs output/data produced by the dependency
                     # sequence — must start after the dependency completes (ordering only)
                     # runtime  — must be deployed/running alongside the dependency

owner: string | null      # Team or role responsible. null if unassigned.
agent_type: string | null # Hint for routing to a specialized AI executor:
                          # architect | api_builder | ui_builder | test_writer | docs_writer | deployer

effort_estimate: string | null  # null, or: "2h", "1d", "3d"

notes: string | null  # Additional context, constraints discovered late, open questions

children:           # Empty list = leaf node (executable by an AI agent)
  - {same schema}   # Populated at execution time via `wbs.py decompose` if a leaf is too large
```

---

## Full tree.yaml example

```yaml
meta:
  project: client-portal
  version: 0.1.0
  prd_source: docs/prd.md
  tech_stack:
    - Python 3.12
    - FastAPI
    - PostgreSQL
    - Redis
    - React 18
  conventions: See .wbs/context.md
  verify:              # Definition of Done — run by `wbs.py done` on EVERY completion
    - pytest -q
    - ruff check .

tree:
  id: ROOT
  type: product
  title: Client portal
  objective: Give clients self-serve access to their account, documents, and support — replacing email-based workflows
  status: pending
  inputs: []
  constraints:
    - WCAG AA accessibility
    - SOC 2 Type II compliance required
  outputs:
    - Deployed client portal (web app + API)
  acceptance_criteria:
    - All capability nodes complete and acceptance-tested
    - Load test: 500 concurrent users at < 2s p95
  dependencies: []
  children:

    - id: CAP-AUTH
      type: capability
      title: Authentication
      objective: Secure, passwordless client login with no IT support burden
      status: pending
      inputs: []
      constraints: []
      outputs:
        - Auth service
      acceptance_criteria:
        - Client can log in via magic link within 60 seconds of request
        - Invalid or expired links are rejected with clear messaging
        - Admin can revoke all active sessions for a client
      dependencies: []
      children:

        - id: AUTH-USER-REPO
          type: work_package
          title: User repository
          objective: Persist and retrieve client accounts by email
          status: pending
          inputs: []
          constraints:
            - Email must be unique per tenant
          outputs:
            - User model
            - get_by_email(tenant_id, email) → User | None
            - create_or_get(tenant_id, email) → User
          acceptance_criteria:
            - get_by_email returns None for unknown email
            - Duplicate email within same tenant raises conflict error
            - Cross-tenant isolation: same email in different tenants returns separate records
          dependencies: []
          agent_type: api_builder
          effort_estimate: 4h
          owner: null
          notes: null
          children: []

        - id: AUTH-MAGICLINK-API
          type: work_package
          title: Magic-link request endpoint
          objective: Accept an email address and issue a short-lived signed login token
          status: pending
          inputs:
            - User model (AUTH-USER-REPO)
          constraints:
            - Stateless API — no session stored server-side
            - Token expiry: 15 minutes
            - Rate limit: 5 requests per email per hour
          outputs:
            - POST /auth/magic-link endpoint
            - Signed token stored in Redis with TTL
            - Email dispatch call (to mail service)
          acceptance_criteria:
            - Invalid email format → 422
            - Valid request → 200, email dispatched (mocked in tests)
            - Token stored in Redis with 15-minute TTL
            - 6th request within 1 hour → 429
          dependencies:
            - id: AUTH-USER-REPO
              type: data
          agent_type: api_builder
          effort_estimate: 1d
          owner: null
          notes: null
          children: []
```

---

## context.md format

`.wbs/context.md` is loaded by the AI executor alongside every leaf node. Keep it factual and dense — no narrative.

```markdown
# Project Context

## Tech Stack
- Python 3.12, FastAPI, Pydantic v2
- PostgreSQL 16 (primary store), Redis 7 (cache + token TTLs)
- React 18 + TypeScript, Vite, Tailwind CSS
- Docker + GitHub Actions CI

## Core Design Concepts
- One unifying mental model in 1–3 bullets, e.g.:
- Everything is a tenant-scoped resource; the JWT is the sole source of tenant identity
- Passwordless-only: no credential storage anywhere in the system

## Design Alternatives
- One line per rejected path: what it was, why it was pruned. Do not re-litigate these at execution time.
- e.g. Session cookies rejected: stateless API requirement; JWT chosen despite revocation complexity

## Conventions
- API: RESTful, versioned under /api/v1/, snake_case JSON
- Auth: JWT bearer tokens, issued after magic-link verification
- Tests: pytest, httpx for API tests; vitest for frontend; no mocks for DB (use test DB)
- Test files: tests/{domain}/test_{unit}.py — leaf `verify` commands point here

## Definition of Done
- Commands every node must pass before `done` (mirrored in tree.yaml `meta.verify`):
- `pytest -q` · `ruff check .` · `mypy backend/`
- Errors: RFC 9457 Problem Details format

## Architecture Notes
- Monorepo: backend/ (FastAPI), frontend/ (React), infra/ (Docker/CI)
- Multi-tenant: every query scoped by tenant_id from JWT claims
- Mail: abstracted behind MailService interface; SMTP in prod, in-memory mock in tests

## Non-Functional Requirements
- p95 response time < 200ms for all API endpoints under 500 concurrent users
- SOC 2 Type II: all PII encrypted at rest, audit log for auth events
- WCAG AA: frontend components must pass axe-core automated checks

## Open Questions
- Unresolved items from the contracting point. Executors flag (not guess) if a leaf depends on one.

## Learnings
- Dated entries appended on tree revisions: what building revealed about the problem, not just the plan.
```
