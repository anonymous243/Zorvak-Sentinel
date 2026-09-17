from datetime import datetime, timezone
import json
from uuid import uuid4, UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sentinel_core.authorization import ActionRequest, DecisionEffect, DecisionReason
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.authorization_service import authorize
from sentinel_core.execution import ActionExecutor, ExecutionStatus, ExecutionReconciler, ReconciliationResult
from sentinel_core.models import ExecutionRecord, ExecutionReconciliation
from sentinel_core.events import ActionExecutionEvent, ActionReconciliationEvent, serialize_event
from sentinel_core import outbox_service

class GatewayExecutionResult:
    """
    The final outcome returned by the Action Gateway.
    """
    def __init__(self, execution_id: str, status: ExecutionStatus, authorization_decision_id: str):
        self.execution_id = execution_id
        self.status = status
        self.authorization_decision_id = authorization_decision_id

async def _get_existing_execution(session: AsyncSession, tenant_id: str, request_id: str) -> ExecutionRecord | None:
    res = await session.execute(
        select(ExecutionRecord)
        .where(ExecutionRecord.tenant_id == tenant_id)
        .where(ExecutionRecord.request_id == request_id)
    )
    return res.scalar_one_or_none()


async def enforce_and_execute(
    session_factory: async_sessionmaker[AsyncSession],
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    executor: ActionExecutor,
    signature: str,
    signing_key_id: str,
    timestamp: datetime,
) -> GatewayExecutionResult:
    """
    The single controlled action-execution boundary.
    Enforces that execution only occurs if authorization explicitly ALLOWS it.
    """
    
    execution_id = str(uuid4())
    
    # ---------------------------------------------------------
    # PHASE 1 & 2: AUTHORIZATION & EXECUTION INTENT
    # ---------------------------------------------------------
    try:
        async with session_factory() as session:
            async with session.begin():
                
                # Verify request identity matches principal identity
                if request.agent_id != principal.agent_id:
                    raise ValueError("ActionRequest agent_id does not match AuthenticatedPrincipal")

                # Verify Request Signature and Timestamp freshness
                from sentinel_core.signing_key_service import verify_agent_request_signature
                is_valid = await verify_agent_request_signature(
                    session=session,
                    request=request,
                    principal=principal,
                    timestamp=timestamp,
                    signature=signature,
                    signing_key_id=signing_key_id
                )
                if not is_valid:
                    raise ValueError("Request signature verification failed")

                # Check for idempotency before authorizing, if possible, but authorization
                # audit dictates we probably should do the check first to avoid
                # generating duplicate authorization records.
                existing = await _get_existing_execution(session, principal.tenant_id, str(request.request_id))
                if existing:
                    return GatewayExecutionResult(
                        execution_id=existing.id,
                        status=ExecutionStatus(existing.status),
                        authorization_decision_id=existing.authorization_decision_id
                    )

                decision = await authorize(session, request, principal)
                
                if not decision.allowed:
                    # Execution is blocked
                    record = ExecutionRecord(
                        id=execution_id,
                        tenant_id=principal.tenant_id,
                        agent_id=principal.agent_id,
                        request_id=str(request.request_id),
                        authorization_decision_id=str(decision.decision_id),
                        risk_assessment_id=str(decision.risk_assessment_id) if decision.risk_assessment_id else None,
                        policy_id=decision.policy_id,
                        policy_version_id=decision.policy_version_id,
                        action=decision.action,
                        resource=decision.resource,
                        tool_id=decision.tool_id,
                        capability_id=decision.capability_id,
                        status=ExecutionStatus.NOT_EXECUTED.value,
                    )
                    session.add(record)
                    # We commit here to persist NOT_EXECUTED.
                else:
                    # ALLOW -> Execution Intent
                    record = ExecutionRecord(
                        id=execution_id,
                        tenant_id=principal.tenant_id,
                        agent_id=principal.agent_id,
                        request_id=str(request.request_id),
                        authorization_decision_id=str(decision.decision_id),
                        risk_assessment_id=str(decision.risk_assessment_id) if decision.risk_assessment_id else None,
                        policy_id=decision.policy_id,
                        policy_version_id=decision.policy_version_id,
                        action=decision.action,
                        resource=decision.resource,
                        tool_id=decision.tool_id,
                        capability_id=decision.capability_id,
                        status=ExecutionStatus.EXECUTION_PENDING.value,
                    )
                    session.add(record)
    except IntegrityError:
        # A concurrent request beat us to creating the ExecutionRecord for this tenant_id + request_id.
        # We catch the exception, let the session rollback, and fetch the winner.
        async with session_factory() as session:
            async with session.begin():
                existing = await _get_existing_execution(session, principal.tenant_id, str(request.request_id))
                if existing:
                    return GatewayExecutionResult(
                        execution_id=existing.id,
                        status=ExecutionStatus(existing.status),
                        authorization_decision_id=existing.authorization_decision_id
                    )
                else:
                    # Very strange concurrency artifact if it's missing, but fail safe.
                    raise RuntimeError("Failed to resolve concurrent execution creation.")

    # Check if we were blocked by authorization
    if not decision.allowed:
        return GatewayExecutionResult(
            execution_id=execution_id,
            status=ExecutionStatus.NOT_EXECUTED,
            authorization_decision_id=str(decision.decision_id)
        )
            
    # Session commits and closes automatically here
    
    # ---------------------------------------------------------
    # PHASE 3: EXTERNAL EXECUTION
    # ---------------------------------------------------------
    try:
        executor_result = await executor.execute(request, principal)
        final_status = executor_result.status
    except ValueError:
        # e.g., Pre-dispatch validation exception -> definitely failed
        final_status = ExecutionStatus.EXECUTION_FAILED
    except Exception:
        # Ambiguous exception, possibly post-dispatch -> unknown
        final_status = ExecutionStatus.EXECUTION_UNKNOWN

    # ---------------------------------------------------------
    # PHASE 4: OUTCOME PERSISTENCE
    # ---------------------------------------------------------
    async with session_factory() as session:
        async with session.begin():
            # Reload the execution record
            record_res = await session.execute(
                select(ExecutionRecord).where(ExecutionRecord.id == execution_id)
            )
            record = record_res.scalar_one()
            
            # Update status
            record.status = final_status.value
            
            from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate
            
            if final_status == ExecutionStatus.EXECUTION_FAILED:
                await persist_security_event(session, SecurityEventCreate(
                    tenant_id=principal.tenant_id,
                    event_type="EXECUTION_FAILED",
                    occurred_at=datetime.now(timezone.utc),
                    outcome="FAILURE",
                    agent_id=principal.agent_id,
                    credential_id=principal.credential_id,
                    tool_id=decision.tool_id,
                    policy_id=decision.policy_id,
                    policy_version_id=decision.policy_version_id,
                    execution_id=execution_id,
                    authorization_decision_id=str(decision.decision_id),
                    request_id=str(request.request_id),
                    reason_code="execution_failed",
                ))
            elif final_status == ExecutionStatus.EXECUTION_UNKNOWN:
                await persist_security_event(session, SecurityEventCreate(
                    tenant_id=principal.tenant_id,
                    event_type="EXECUTION_UNKNOWN",
                    occurred_at=datetime.now(timezone.utc),
                    outcome="UNKNOWN",
                    agent_id=principal.agent_id,
                    credential_id=principal.credential_id,
                    tool_id=decision.tool_id,
                    policy_id=decision.policy_id,
                    policy_version_id=decision.policy_version_id,
                    execution_id=execution_id,
                    authorization_decision_id=str(decision.decision_id),
                    request_id=str(request.request_id),
                    reason_code="execution_ambiguous",
                ))
            
            # Create execution event
            event = ActionExecutionEvent(
                execution_id=UUID(execution_id),
                request_id=request.request_id,
                decision_id=decision.decision_id,
                risk_assessment_id=decision.risk_assessment_id,
                tenant_id=principal.tenant_id,
                agent_id=principal.agent_id,
                action=decision.action,
                resource=decision.resource,
                status=final_status.value,
                policy_id=decision.policy_id,
                policy_version_id=decision.policy_version_id,
                tool_id=decision.tool_id,
                capability_id=decision.capability_id,
                occurred_at=datetime.now(timezone.utc),
            )
            
            # Persist via outbox
            await outbox_service.create_event(
                session=session,
                event_type=event.event_type,
                aggregate_type="execution",
                aggregate_id=execution_id,
                payload=serialize_event(event),
                occurred_at=event.occurred_at,
                correlation_id=str(request.request_id),
            )

    return GatewayExecutionResult(
        execution_id=execution_id,
        status=final_status,
        authorization_decision_id=str(decision.decision_id)
    )

async def reconcile_execution(
    session_factory: async_sessionmaker[AsyncSession],
    execution_id: str,
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    reconciler: ExecutionReconciler
) -> GatewayExecutionResult:
    """
    Safely reconcile an EXECUTION_UNKNOWN state.
    """
    # 1. Load execution
    async with session_factory() as session:
        async with session.begin():
            res = await session.execute(
                select(ExecutionRecord)
                .where(ExecutionRecord.id == execution_id)
                .where(ExecutionRecord.tenant_id == principal.tenant_id)
            )
            record = res.scalar_one_or_none()
            if not record:
                raise ValueError("Execution not found or belongs to different tenant.")
            
            if record.status != ExecutionStatus.EXECUTION_UNKNOWN.value:
                raise ValueError(f"Cannot reconcile execution in state: {record.status}")
                
            authorization_decision_id = record.authorization_decision_id

    # 2. Call reconciler OUTSIDE transaction
    reconciliation_result, metadata = await reconciler.reconcile(execution_id, request, principal)
    
    # 3. Determine resulting terminal state
    if reconciliation_result == ReconciliationResult.DID_EXECUTE:
        new_status = ExecutionStatus.EXECUTED
    elif reconciliation_result == ReconciliationResult.DID_NOT_EXECUTE:
        new_status = ExecutionStatus.EXECUTION_FAILED
    else:
        new_status = ExecutionStatus.EXECUTION_UNKNOWN

    # 4. Persist result atomically
    reconciliation_id = str(uuid4())
    async with session_factory() as session:
        async with session.begin():
            res = await session.execute(
                select(ExecutionRecord).where(ExecutionRecord.id == execution_id)
            )
            record = res.scalar_one()
            
            # Only update if the status is still UNKNOWN
            # (concurrency check)
            if record.status == ExecutionStatus.EXECUTION_UNKNOWN.value:
                record.status = new_status.value
            else:
                new_status = ExecutionStatus(record.status)

            reconciliation = ExecutionReconciliation(
                id=reconciliation_id,
                execution_id=execution_id,
                tenant_id=principal.tenant_id,
                agent_id=principal.agent_id,
                reconciler_type=reconciler.__class__.__name__,
                result=reconciliation_result.value,
                metadata_json=json.dumps(metadata),
                completed_at=datetime.now(timezone.utc),
            )
            session.add(reconciliation)
            
            event = ActionReconciliationEvent(
                reconciliation_id=UUID(reconciliation_id),
                execution_id=UUID(execution_id),
                request_id=UUID(record.request_id),
                tenant_id=principal.tenant_id,
                agent_id=principal.agent_id,
                reconciliation_result=reconciliation_result.value,
                resulting_status=new_status.value,
                occurred_at=reconciliation.completed_at,
            )
            
            await outbox_service.create_event(
                session=session,
                event_type=event.event_type,
                aggregate_type="execution_reconciliation",
                aggregate_id=reconciliation_id,
                payload=serialize_event(event),
                occurred_at=event.occurred_at,
                correlation_id=str(record.request_id),
            )

    return GatewayExecutionResult(
        execution_id=execution_id,
        status=new_status,
        authorization_decision_id=authorization_decision_id
    )
