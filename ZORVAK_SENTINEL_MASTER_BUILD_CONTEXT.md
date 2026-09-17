# ZORVAK SENTINEL — MASTER BUILD CONTEXT

## Mission

ZORVAK SENTINEL is a serious security/control plane for autonomous systems,
especially autonomous AI agents.

Core goals:

- trusted agent identity
- request authentication and signing
- capability security
- policy authorization
- deterministic risk evaluation
- runtime enforcement
- execution reliability
- immutable/auditable security history
- incident detection
- eventually alerting, investigation, analytics, autonomous defense,
  multi-agent trust, and production-scale security

Build security infrastructure, not demo CRUD.

---

# 1. NON-NEGOTIABLE ENGINEERING RULES

1. One stage at a time.
2. Never proceed until the current stage is implemented and verified.
3. Never claim completion without actual test/migration evidence.
4. Preserve all earlier security invariants.
5. Fail closed when security state is ambiguous.
6. Tenant isolation is mandatory everywhere.
7. `AuthenticatedPrincipal.tenant_id` is authoritative.
8. Never trust arbitrary request-body tenant IDs.
9. Never invent identity, telemetry, authorization context, or database
   semantics.
10. Never store secrets in logs, events, evidence, metadata, or API responses.
11. The Unit of Work owns commit/rollback.
12. Services must NOT call `session.rollback()`.
13. Do not create independent transactions merely to make telemetry survive.
14. SQLite is development/test only; never claim it proves PostgreSQL-specific
    locking/concurrency semantics.
15. Use Alembic for schema changes.
16. Never modify old migrations.
17. Never silently delete, merge, or rewrite existing security data.
18. Do not weaken/remove tests to obtain green results.
19. Avoid unrelated refactors.
20. Do not implement future stages early.
21. Keep security decisions deterministic and explainable.
22. Historical security records should be immutable/append-only where defined.
23. Do not introduce ML/AI as a substitute for deterministic controls unless
    the stage explicitly requires it.
24. Do not expose public APIs that allow arbitrary callers to manufacture
    security records.
25. If a prerequisite is missing, stop and identify it rather than fabricating
    a solution.
26. Never use SQLite test behavior as evidence of PostgreSQL row-lock behavior.
27. Every completed stage must have a precise final report.

---

# 2. PROJECT

Path:

`/home/amar/Desktop/zorvak sentinal`

Environment:

- Python 3.12.3
- `.venv`
- SQLite development DB
- FastAPI
- async SQLAlchemy
- Alembic
- bcrypt
- cryptography / Ed25519
- pytest

Core structure:

```text
apps/api/src/sentinel_api/
packages/core/src/sentinel_core/
tests/
migrations/versions/
alembic.ini
requirements.txt
sentinel.db
```

Important core files include:

```text
database.py
models.py
schemas.py
agent_service.py
policy_service.py
authorization.py
authorization_service.py
decision_engine.py
outbox_service.py
outbox_dispatcher.py
events.py
principals.py
authentication_service.py
risk.py
risk_engine.py
combiner.py
execution.py
action_gateway.py
capability_service.py
request_signing.py
signing_key_service.py
policy_validator.py
conflict_analyzer.py
policy_simulator.py
```

---

# 3. COMPLETED FOUNDATION

## Phase 0 — Engineering Foundation

Complete:

- FastAPI
- async SQLAlchemy
- Alembic
- request-scoped UoW
- commit/rollback ownership
- tests

UoW principle:

```python
async def get_session():
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise
```

Services do not own rollback.

---

# 4. COMPLETED SECURITY ARCHITECTURE

## Phase 1 — Policy & Authorization

Complete:

- ALLOW/DENY decisions
- deterministic decision reasons
- strict/frozen ActionRequest
- AuthorizationDecision
- Policy
- immutable PolicyVersion
- active version
- tenant-scoped policies
- immutable PolicyVersion fields
- fail-closed authorization

## Phase 2 — Durable Events & Audit

Complete:

- transactional outbox
- pending/processing/published/failed/dead_letter
- attempts/leases/backoff
- stable event IDs
- correlation IDs
- deterministic canonical event JSON
- no secrets
- at-least-once semantics

## Phase 3 — Agent Identity

Complete:

- Tenant
- Agent
- AgentCredential
- bcrypt secret hashing
- no plaintext credentials
- AuthenticatedPrincipal
- active tenant/agent validation
- credential lifecycle
- expiry checks
- generic fail-closed auth errors
- last-used tracking

## Phase 4 — Risk / Behavioral Decisioning

Complete.

Risk levels:

- LOW
- MEDIUM
- HIGH
- CRITICAL

Risk statuses:

- SUCCESS
- UNKNOWN
- ERROR

Factors include:

- SENSITIVE_ACTION
- SENSITIVE_RESOURCE
- BEHAVIORAL_DEVIATION
- ANOMALOUS_CONTEXT

Combiner:

```text
policy DENY + any risk -> DENY
policy ALLOW + LOW/MEDIUM/HIGH -> ALLOW
policy ALLOW + CRITICAL -> DENY / RISK_DENIED
policy ALLOW + UNKNOWN/ERROR -> DENY / RISK_EVALUATION_ERROR
```

## Phase 5 — Runtime Enforcement

Complete.

Execution statuses:

- NOT_EXECUTED
- EXECUTION_PENDING
- EXECUTION_STARTED
- EXECUTED
- EXECUTION_FAILED
- EXECUTION_UNKNOWN

Denied requests never execute.

Unknown executor exceptions become UNKNOWN.

No automatic retry.

## Phase 6 — Execution Reliability

Complete:

- `(tenant_id, request_id)` idempotency
- duplicate request protection
- reconciliation history
- UNKNOWN reconciliation
- DID_EXECUTE -> EXECUTED
- DID_NOT_EXECUTE -> EXECUTION_FAILED
- STILL_UNKNOWN -> UNKNOWN
- no automatic retry

## Phase 7 — Tool & Capability Security

Complete:

- tenant-scoped Tool
- tenant-scoped Capability
- ToolActionCapability
- AgentCapability
- resource scopes
- grant/revoke/expiry
- exact/wildcard capability checks
- capability check after idempotency
- capability failure -> DENY / CAPABILITY_DENIED

## Phase 8 — Identity & Trust Hardening

Complete:

- AgentSigningKey
- Ed25519 request signing
- signing-key ownership
- active/nonexpired validation
- signature verification
- timestamp freshness
- malformed/stale/future handling
- last-used tracking
- fail-closed identity verification
- signing verification before idempotency
- strict agent match

Signed fields:

- tenant_id
- agent_id
- request_id
- tool_id
- action
- resource
- timestamp

Caller context is currently excluded from signed payload.

---

# 5. PHASE 9 — POLICY GOVERNANCE

Stages 1–9 are COMPLETE.

## Stage 1
Inspected existing Policy/PolicyVersion architecture.

## Stage 2
Added:

- tenant_id to Policy
- tenant_id to PolicyVersion
- tenant-scoped names
- lifecycle:
  draft
  review
  approved
  published
  active
  deprecated
- tenant ownership
- Policy/PolicyVersion tenant invariant

## Stage 3
Deterministic precedence:

1. enabled policies
2. action/resource matching
3. specificity
4. highest priority
5. DENY wins ties
6. Policy.id tie-break
7. no match -> DENY

Invalid candidate state fails closed.

## Stage 4
Pure deterministic policy validator.

Validates:

- action/resource
- lifecycle
- effect
- priority 0–9999
- exact/prefix/total wildcard grammar
- invalid wildcard forms
- active-version integrity

## Stage 5
`conflict_analyzer.py`

Detects:

- OVERLAP
- SHADOWED
- CONTRADICTION
- REDUNDANT

Advisory only.

Deterministic and tenant scoped.

## Stage 6
`policy_simulator.py`

API:

`POST /policies/simulate`

Simulation:

- deterministic
- detached/in-memory
- no ORM mutation
- candidate not persisted
- no decision persistence
- no execution
- no outbox mutation
- principal tenant authoritative

## Stage 7
Rollback:

- PolicyRollbackRequest
- PolicyRollbackResult
- tenant checks
- active-state checks
- already-active no-op
- target validation
- previous active -> deprecated
- target -> active
- active_version_id update
- immutable history

## Stage 8
`PolicyAuditRecord`

Operations:

- POLICY_CREATED
- POLICY_VERSION_CREATED
- POLICY_VERSION_ACTIVATED
- POLICY_VERSION_ROLLED_BACK

Synchronous and same UoW.

Migration:

`95f2281fc5f1`

Stage 8:

`176 passed`

## Stage 9
Strong single-active enforcement.

Invariant:

```text
For every Policy:
AT MOST ONE PolicyVersion may be active.
```

DB partial unique index:

`ix_policy_versions_single_active`

Equivalent:

```python
Index(
    "ix_policy_versions_single_active",
    "policy_id",
    sqlite_where=text("status = 'active'"),
    postgresql_where=text("status = 'active'"),
    unique=True,
)
```

Migration:

`303775cb2bfe`

Application protection:

- parent Policy `with_for_update()` where supported
- deliberate deprecation ordering
- explicit flush
- IntegrityError -> PolicyConcurrencyException
- service does not rollback
- UoW owns rollback
- API -> HTTP 409
- deterministic safe concurrency message
- audit remains transactionally coupled

Stage 9 final:

`189 passed`

SQLite limitation documented: SQLite does not empirically prove PostgreSQL
row-lock serialization.

---

# 6. CURRENT STAGE STATUS

## Phase 9 Stage 10 — Incident Detection

BLOCKED.

Reason:

Existing authentication/signature paths do not persist enough authoritative
historical telemetry.

For example:

```text
authentication failure
    -> exception
    -> request ends
    -> no durable historical security signal
```

Therefore the system cannot reliably detect:

```text
5 authentication failures
within 5 minutes
for the same agent
```

without first establishing telemetry.

Similarly, request-signature failures may occur before enough trusted tenant
context exists to create a tenant-scoped event.

DO NOT fake these signals.

---

# 7. IMMEDIATE NEXT STAGE

## Phase 9 Stage 10A — Security Telemetry Foundation

This is the current task.

Purpose:

Create a minimal generic authoritative `SecurityEvent` foundation.

Concept:

```text
existing trusted security operation
          |
          v
SecurityEvent service
          |
          v
append-only SecurityEvent
          |
          v
future Stage 10 detector
```

Stage 10A is NOT Incident Detection.

Do NOT implement:

- Incident
- IncidentAuditRecord
- detection thresholds
- incident deduplication
- incident APIs
- alerts
- notifications
- SIEM
- dashboards
- remediation
- AI detection
- autonomous response

---

# 8. STAGE 10A — SECURITY EVENT MODEL

Create:

`SecurityEvent`

Fields:

- id
- tenant_id
- event_type
- occurred_at
- agent_id nullable
- credential_id nullable
- tool_id nullable
- policy_id nullable
- policy_version_id nullable
- execution_id nullable
- authorization_decision_id nullable
- correlation_id nullable
- request_id nullable
- outcome
- reason_code nullable
- metadata
- created_at

Use existing ID/time conventions.

Do not duplicate existing authoritative state unnecessarily.

---

# 9. STAGE 10A — EVENT TYPES

Initial intended types:

```text
AUTHENTICATION_FAILURE
AUTHENTICATION_SUCCESS
INVALID_REQUEST_SIGNATURE
CAPABILITY_DENIED
POLICY_DENIED
RISK_CRITICAL
RISK_EVALUATION_FAILURE
EXECUTION_UNKNOWN
EXECUTION_FAILED
```

Only mark an event type SUPPORTED if an authoritative existing code path can
safely emit it.

Unsupported types must be explicitly documented.

---

# 10. OUTCOMES

Use:

```text
SUCCESS
FAILURE
UNKNOWN
```

Reason codes must be stable machine-readable values.

Never blindly persist raw exception strings.

---

# 11. SECURITY EVENT SERVICE

Create:

`packages/core/src/sentinel_core/security_event_service.py`

Responsibilities:

- create SecurityEvent
- validate trusted tenant context
- validate trusted identity references
- validate event type/outcome
- sanitize metadata
- enforce bounded metadata
- prevent secret persistence

No public arbitrary event-creation API.

No normal update/delete service methods.

---

# 12. TENANT RULES

`tenant_id` must come from authoritative security context.

Never:

- guess tenant
- derive tenant from arbitrary body data
- assign unknown-agent failures to a guessed tenant
- create cross-tenant events

If tenant cannot safely be established:

DO NOT create a tenant-scoped event.

Document this limitation.

Agent/credential/tool/policy/execution/authorization references must be
tenant-consistent.

---

# 13. TRANSACTION RULES

Follow the existing UoW.

Services must NOT call:

```python
session.rollback()
```

Successful operation:

```text
operation
 -> SecurityEvent
 -> commit
```

Failed operation:

```text
operation
 -> SecurityEvent
 -> exception
 -> UoW rollback
```

Do NOT create a second independent transaction merely to make telemetry
survive.

If a failure event cannot survive because the existing UoW rolls back,
document that limitation rather than inventing a separate transaction model.

---

# 14. AUTHENTICATION EVENTS

Inspect the exact authentication path and UoW boundary.

Potential:

- AUTHENTICATION_SUCCESS
- AUTHENTICATION_FAILURE

Only emit when:

- fact is authoritative
- safe identity/context exists
- tenant can safely be established
- transaction semantics are understood

Never store credentials/secrets.

If failure telemetry cannot survive current rollback semantics, document it.

Do not weaken authentication behavior.

---

# 15. SIGNATURE EVENTS

Inspect:

- request_signing.py
- signing_key_service.py

Potential:

`INVALID_REQUEST_SIGNATURE`

Preserve:

- Ed25519 behavior
- canonicalization
- freshness
- key ownership
- fail-closed semantics

Never store:

- signature bytes
- private keys
- secrets
- bearer tokens
- authorization headers
- raw signed payloads

If tenant identity is unavailable, do not guess it.

---

# 16. OTHER EVENTS

Where authoritative facts exist:

### Capability
`CAPABILITY_DENIED`

### Authorization
`POLICY_DENIED`

Use existing AuthorizationDecisionRecord.

### Risk
`RISK_CRITICAL`
`RISK_EVALUATION_FAILURE`

Use authoritative risk results.

### Execution
`EXECUTION_UNKNOWN`
`EXECUTION_FAILED`

Use actual state transitions.

Avoid duplicate emission when multiple functions observe the same outcome.

---

# 17. NO DUPLICATE SOURCE OF TRUTH

SecurityEvent is telemetry for future detection.

It does NOT replace:

- AuthorizationDecisionRecord
- RiskRecord
- ExecutionRecord
- PolicyAuditRecord
- transactional outbox

Existing records remain authoritative.

Reference existing IDs where useful.

---

# 18. APPEND-ONLY

SecurityEvent is append-only at application level.

No:

- update service
- delete service
- post-creation mutation

Do not add complicated DB triggers unless genuinely necessary.

---

# 19. METADATA SAFETY

Metadata must be bounded.

Never persist:

- passwords
- credential secrets
- private keys
- signatures
- bearer tokens
- authorization headers
- sensitive raw payloads
- stack traces
- arbitrary exception strings

Prefer:

- reason codes
- authoritative IDs
- timestamps
- correlation IDs
- request IDs
- concise safe metadata

---

# 20. DATABASE INDEXES

Use only justified detection-query indexes:

- tenant_id + occurred_at
- tenant_id + event_type + occurred_at
- tenant_id + agent_id + occurred_at
- tenant_id + correlation_id
- request_id

Use Alembic.

---

# 21. MIGRATION

Before migration:

- inspect current migration head
- inspect schema
- check naming conflicts
- check for existing SecurityEvent conflicts

Never modify old migrations.

Run:

```bash
PYTHONPATH=packages/core/src:apps/api/src .venv/bin/alembic upgrade head

PYTHONPATH=packages/core/src:apps/api/src .venv/bin/alembic check

PYTHONPATH=packages/core/src:apps/api/src .venv/bin/alembic current
```

---

# 22. TESTS

Create:

`tests/test_security_events.py`

Cover:

1. SecurityEvent creation
2. strict event type
3. strict outcome
4. tenant association
5. agent association
6. safe reason code
7. bounded metadata
8. no secret persistence
9. append-only behavior
10. no arbitrary public creation API
11. tenant isolation
12. agent/tenant consistency
13. successful transaction persistence
14. failed transaction behavior
15. authentication success where supported
16. authentication failure where supported
17. invalid signature where supported
18. capability denial
19. policy denial
20. CRITICAL risk
21. risk evaluation failure
22. EXECUTION_UNKNOWN
23. EXECUTION_FAILED
24. no duplicate event for one authoritative outcome
25. migration/schema correctness

Do not create fake tests for unsupported signals.

---

# 23. REGRESSION PROTECTION

Do not weaken:

- authentication
- bcrypt verification
- Ed25519 verification
- freshness checks
- signing-key ownership
- tenant isolation
- capability enforcement
- policy precedence
- risk combination
- execution state machine
- idempotency
- audit
- outbox
- rollback
- Stage 9 concurrency protection

Telemetry must be additive.

---

# 24. SECURITY REVIEW

Explicitly inspect for:

- tenant escape
- IDOR
- caller-controlled tenant_id
- arbitrary event injection
- secret leakage
- raw exception leakage
- sensitive payload storage
- incorrect agent/tenant association
- duplicate sources of truth
- rollback inconsistency
- transaction boundary changes
- event tampering
- update/delete paths

Fail closed where security state is ambiguous.

---

# 25. SQLITE / POSTGRESQL

Development uses SQLite.

SQLite verification may establish:

- schema correctness
- index correctness
- supported transaction behavior
- application behavior

It does NOT prove:

- PostgreSQL row locks
- PostgreSQL isolation semantics
- PostgreSQL-specific concurrency

Never claim otherwise.

---

# 26. TEST VERIFICATION

Run focused:

```bash
PYTHONPATH=packages/core/src:apps/api/src .venv/bin/pytest tests/test_security_events.py -v
```

Then relevant modified tests.

Then FULL SUITE:

```bash
PYTHONPATH=packages/core/src:apps/api/src .venv/bin/pytest tests/ -v
```

Baseline:

`189 passed`

Final must have:

- zero failures
- zero errors

Do not report completion from a subset.

---

# 27. DOCUMENTATION

Update:

- `task.md`
- `walkthrough.md`

Document:

- why Stage 10 was blocked
- why Stage 10A exists
- SecurityEvent schema
- supported events
- unsupported events
- authoritative source for each event
- tenant-context limitations
- transaction behavior
- append-only behavior
- secret handling
- indexes
- migration
- tests
- SQLite/PostgreSQL limitations

Clearly distinguish:

```text
Stage 10A = Security Telemetry Foundation
Stage 10  = Incident Detection
Stage 11  = Alerting
```

---

# 28. STAGE 10A COMPLETION

Mark:

## COMPLETE

when the telemetry foundation is implemented and verified.

Or:

## COMPLETE WITH DOCUMENTED LIMITATIONS

when the foundation is sound but some signals cannot safely be persisted due
to missing trusted context or existing transaction boundaries.

Do not falsely claim unsupported signals.

---

# 29. AFTER 10A

Only after 10A is verified, implement:

## Phase 9 Stage 10 — Incident Detection

Expected scope:

- Incident model
- IncidentAuditRecord
- deterministic detection rules
- thresholds/windows
- deduplication
- active incident DB uniqueness
- lifecycle
- bounded evidence
- tenant isolation
- APIs
- transactional audit
- adversarial tests

Active deduplication invariant:

```text
For a tenant + deduplication_key:
at most one OPEN or ACKNOWLEDGED incident
```

Conceptually:

```sql
UNIQUE (tenant_id, deduplication_key)
WHERE status IN ('open', 'acknowledged')
```

Resolved incidents must allow future incidents.

---

# 30. FUTURE ROADMAP

After Incident Detection:

## Stage 11 — Alerting

- alert lifecycle
- delivery
- notification channels
- escalation
- alert deduplication
- delivery reliability

## Stage 12 — Evidence & Investigation

- evidence chains
- investigations
- forensic timelines
- incident correlation
- evidence integrity

## Stage 13 — Analytics

- security analytics
- agent behavior trends
- attack patterns
- operational intelligence
- metrics

## Stage 14 — Autonomous Security / AI Defense

- AI-assisted detection
- adaptive security
- controlled autonomous defense
- automated defensive reasoning

## Stage 15 — Multi-Agent Trust

- agent-to-agent trust
- delegation
- trust propagation
- delegated authority

## Stage 16 — Distributed / Production Security

- PostgreSQL production semantics
- distributed coordination
- HA
- stronger concurrency verification
- production deployment security

## Stage 17 — Assurance

- threat modeling
- formal/security assurance
- compliance evidence
- penetration/security verification

## Stage 18 — Autonomous Systems Security

Long-term objective:

A complete security control plane for autonomous systems and autonomous AI
agents.

---

# 31. NEVER DO THESE

Never:

- guess tenant identity
- invent telemetry
- store secrets
- store raw credentials
- expose internal exceptions
- allow arbitrary security-event creation
- create unapproved independent telemetry transactions
- claim SQLite proves PostgreSQL concurrency
- silently delete security data
- bypass UoW rollback ownership
- weaken tests
- remove assertions
- skip security tests
- implement future stages early
- claim a stage complete without actual verification

---

# 32. CURRENT DIRECTIVE

Treat this document as the persistent project brief.

Current state:

**Phase 9 Stages 1–9: COMPLETE**

**Phase 9 Stage 10: BLOCKED**

**Phase 9 Stage 10A: CURRENT TASK**

Immediate instruction:

> Implement and verify Stage 10A according to this document. Resolve all
> prerequisites that can be resolved safely within the existing architecture.
> If a signal cannot safely be persisted, document it rather than fabricating
> telemetry. After Stage 10A is fully verified, STOP and report. Do not
> implement Stage 10 Incident Detection until Stage 10A is complete.

Every future stage must be implemented and fully verified before proceeding.
