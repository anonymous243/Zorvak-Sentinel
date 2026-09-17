from __future__ import annotations

import json
from sentinel_core.authorization import AuthorizationDecision
from sentinel_core.models import AuthorizationDecisionRecord, RiskAssessmentRecord
from sentinel_core.risk import RiskAssessment
from sqlalchemy.ext.asyncio import AsyncSession


async def record_decision(
    session: AsyncSession,
    decision: AuthorizationDecision,
    risk_assessment: RiskAssessment | None = None,
) -> AuthorizationDecisionRecord:
    """
    Persist a completed authorization decision and its associated risk assessment.

    Decision records are append-only by design. This service intentionally
    exposes creation only; updates and deletes are not part of the domain API.
    """

    if risk_assessment:
        risk_record = RiskAssessmentRecord(
            id=str(risk_assessment.id),
            tenant_id=risk_assessment.tenant_id,
            agent_id=risk_assessment.agent_id,
            request_id=str(risk_assessment.request_id),
            credential_id=risk_assessment.credential_id,
            score=risk_assessment.score,
            level=risk_assessment.level.value,
            factors=json.dumps([f.value for f in risk_assessment.factors]),
            status=risk_assessment.status.value,
            evaluated_at=risk_assessment.evaluated_at,
            evaluation_ms=risk_assessment.evaluation_ms,
        )
        session.add(risk_record)

        from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate
        from datetime import datetime, timezone
        from sentinel_core.risk import RiskLevel, RiskEvaluationStatus

        if risk_assessment.level == RiskLevel.CRITICAL:
            await persist_security_event(session, SecurityEventCreate(
                tenant_id=risk_assessment.tenant_id,
                event_type="RISK_CRITICAL",
                occurred_at=datetime.now(timezone.utc),
                outcome="FAILURE",
                agent_id=risk_assessment.agent_id,
                credential_id=risk_assessment.credential_id,
                request_id=str(risk_assessment.request_id),
                reason_code="critical_risk_score",
                metadata={"score": risk_assessment.score, "factors": [f.value for f in risk_assessment.factors]}
            ))
        elif risk_assessment.status == RiskEvaluationStatus.ERROR:
            await persist_security_event(session, SecurityEventCreate(
                tenant_id=risk_assessment.tenant_id,
                event_type="RISK_EVALUATION_FAILURE",
                occurred_at=datetime.now(timezone.utc),
                outcome="FAILURE",
                agent_id=risk_assessment.agent_id,
                credential_id=risk_assessment.credential_id,
                request_id=str(risk_assessment.request_id),
                reason_code="evaluation_error",
                metadata={"score": risk_assessment.score}
            ))

        await session.flush()

    record = AuthorizationDecisionRecord(
        id=str(decision.decision_id),
        request_id=str(decision.request_id),
        tenant_id=decision.tenant_id,
        agent_id=decision.agent_id,
        credential_id=decision.credential_id,
        action=decision.action,
        resource=decision.resource,
        effect=decision.effect.value,
        reason=decision.reason.value,
        policy_id=decision.policy_id,
        policy_version_id=decision.policy_version_id,
        risk_assessment_id=str(decision.risk_assessment_id) if decision.risk_assessment_id else None,
        evaluated_at=decision.evaluated_at,
        evaluation_ms=decision.evaluation_ms,
    )

    session.add(record)
    
    from sentinel_core import outbox_service
    from sentinel_core.events import AuthorizationDecisionEvent, serialize_event
    
    event_payload = AuthorizationDecisionEvent(
        event_id=decision.decision_id,
        schema_version=2,
        decision_id=decision.decision_id,
        request_id=decision.request_id,
        tenant_id=decision.tenant_id,
        agent_id=decision.agent_id,
        credential_id=decision.credential_id,
        action=decision.action,
        resource=decision.resource,
        effect=decision.effect.value,
        reason=decision.reason.value,
        policy_id=decision.policy_id,
        policy_version_id=decision.policy_version_id,
        risk_assessment_id=decision.risk_assessment_id,
        tool_id=decision.tool_id,
        capability_id=decision.capability_id,
        evaluated_at=decision.evaluated_at,
        evaluation_ms=decision.evaluation_ms,
        occurred_at=decision.evaluated_at,
    )
    
    serialized_payload = serialize_event(event_payload)
    
    await outbox_service.create_event(
        session=session,
        event_type=event_payload.event_type,
        aggregate_type="authorization_decision",
        aggregate_id=str(decision.decision_id),
        payload=serialized_payload,
        occurred_at=decision.evaluated_at,
        correlation_id=str(decision.request_id)
    )

    await session.flush()

    return record
