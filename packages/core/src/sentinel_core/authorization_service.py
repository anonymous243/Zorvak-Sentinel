from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinel_core.authorization import (
    ActionRequest,
    AuthorizationDecision,
    DecisionEffect,
    DecisionReason,
)
from sentinel_core.decision_engine import evaluate_policies
from sentinel_core.decision_service import record_decision
from sentinel_core.models import Agent, Policy


from sentinel_core.principals import AuthenticatedPrincipal


from sentinel_core.combiner import combine_policy_and_risk
from sentinel_core.risk import DummyBehaviorSignalProvider, BehaviorSignalProvider
from sentinel_core.risk_engine import evaluate_risk
from sentinel_core.capability_service import check_capability

async def authorize(
    session: AsyncSession,
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    behavior_provider: BehaviorSignalProvider | None = None,
) -> AuthorizationDecision:
    """
    Authorize an action against the authoritative database state.

    Security invariants:
      - caller must present a valid authenticated principal
      - principal agent_id must match request agent_id (anti-impersonation)
      - unknown agents are denied
      - non-active agents are denied
      - only enabled policies are evaluated
      - policy resolution is delegated to the deterministic decision engine
      - no implicit allow path exists
    """
    if behavior_provider is None:
        behavior_provider = DummyBehaviorSignalProvider()

    if request.agent_id != principal.agent_id:
        raise ValueError("Anti-impersonation failure: request agent_id does not match authenticated principal")

    agent_result = await session.execute(
        select(Agent).where(Agent.id == request.agent_id)
    )
    agent = agent_result.scalar_one_or_none()

    capability_result = await check_capability(
        session, principal, request.tool_id, request.action, request.resource
    )

    if agent is None:
        policy_decision = AuthorizationDecision(
            request_id=request.request_id,
            tenant_id=principal.tenant_id,
            agent_id=request.agent_id,
            credential_id=principal.credential_id,
            tool_id=request.tool_id,
            action=request.action,
            resource=request.resource,
            effect=DecisionEffect.DENY,
            reason=DecisionReason.AGENT_NOT_FOUND,
            evaluation_ms=0.0,
        )
    elif not capability_result.allowed:
        policy_decision = AuthorizationDecision(
            request_id=request.request_id,
            tenant_id=principal.tenant_id,
            agent_id=request.agent_id,
            credential_id=principal.credential_id,
            tool_id=request.tool_id,
            capability_id=capability_result.capability_id,
            action=request.action,
            resource=request.resource,
            effect=DecisionEffect.DENY,
            reason=capability_result.reason or DecisionReason.CAPABILITY_DENIED,
            evaluation_ms=0.0,
        )
    elif agent.status != "active":
        policy_decision = AuthorizationDecision(
            request_id=request.request_id,
            tenant_id=principal.tenant_id,
            agent_id=request.agent_id,
            credential_id=principal.credential_id,
            tool_id=request.tool_id,
            action=request.action,
            resource=request.resource,
            effect=DecisionEffect.DENY,
            reason=DecisionReason.AGENT_DISABLED,
            evaluation_ms=0.0,
        )
    else:
        policy_result = await session.execute(
            select(Policy)
            .options(selectinload(Policy.active_version))
            .where(Policy.tenant_id == principal.tenant_id)
            .where(Policy.enabled.is_(True))
        )
        policies = list(policy_result.scalars().all())

        policy_decision = evaluate_policies(request, policies, principal, capability_id=capability_result.capability_id)

    # Risk evaluation is always deterministic
    risk_assessment = await evaluate_risk(request, principal, behavior_provider)

    # Combine policy and risk deterministically
    final_decision = combine_policy_and_risk(policy_decision, risk_assessment)

    # Record both risk and decision transactionally
    await record_decision(session, final_decision, risk_assessment)

    if final_decision.effect == DecisionEffect.DENY:
        from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate
        from datetime import datetime, timezone
        await persist_security_event(session, SecurityEventCreate(
            tenant_id=principal.tenant_id,
            event_type="POLICY_DENIED",
            occurred_at=datetime.now(timezone.utc),
            outcome="FAILURE",
            agent_id=principal.agent_id,
            credential_id=principal.credential_id,
            tool_id=request.tool_id,
            policy_id=final_decision.policy_id,
            policy_version_id=final_decision.policy_version_id,
            authorization_decision_id=str(final_decision.decision_id),
            request_id=str(request.request_id) if request.request_id else None,
            reason_code=final_decision.reason.value if hasattr(final_decision.reason, "value") else str(final_decision.reason)
        ))

    return final_decision
