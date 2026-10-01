from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
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
    session_factory: async_sessionmaker[AsyncSession] | None = None,
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

    delegation_info = None
    if request.delegation_id:
        from sentinel_core.delegation_service import validate_delegated_request
        del_result = await validate_delegated_request(
            session=session,
            request=request,
            principal=principal,
            delegation_id=request.delegation_id,
            session_factory=session_factory,
        )
        if not del_result.valid:
            reason_enum = DecisionReason.DELEGATION_DENIED
            if del_result.reason == "delegation_not_found":
                reason_enum = DecisionReason.DELEGATION_NOT_FOUND
            elif del_result.reason == "delegation_expired":
                reason_enum = DecisionReason.DELEGATION_EXPIRED
            elif del_result.reason == "delegation_revoked":
                reason_enum = DecisionReason.DELEGATION_REVOKED
            elif del_result.reason in ("action_scope_violation", "resource_scope_violation"):
                reason_enum = DecisionReason.DELEGATION_SCOPE_VIOLATION
            elif del_result.reason == "delegate_identity_mismatch":
                reason_enum = DecisionReason.IMPERSONATION_ATTEMPT

            policy_decision = AuthorizationDecision(
                request_id=request.request_id,
                tenant_id=principal.tenant_id,
                agent_id=request.agent_id,
                credential_id=principal.credential_id,
                tool_id=request.tool_id,
                action=request.action,
                resource=request.resource,
                effect=DecisionEffect.DENY,
                reason=reason_enum,
                delegation_id=request.delegation_id,
                delegator_agent_id=del_result.delegator_agent_id,
                delegate_agent_id=principal.agent_id,
                effective_agent_id=principal.agent_id,
                evaluation_ms=0.0,
            )
            risk_assessment = await evaluate_risk(request, principal, behavior_provider)
            final_decision = combine_policy_and_risk(policy_decision, risk_assessment)
            await record_decision(session, final_decision, risk_assessment, session_factory=session_factory)
            return final_decision

        delegation_info = del_result

    capability_result = await check_capability(
        session, principal, request.tool_id, request.action, request.resource, session_factory=session_factory
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
    elif not capability_result.allowed:
        # If delegation was presented, delegate agent's lack of capability triggers Confused-Deputy protection
        reason = capability_result.reason or DecisionReason.CAPABILITY_DENIED
        if delegation_info is not None:
            reason = DecisionReason.CONFUSED_DEPUTY_DENIED
            from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate
            from datetime import datetime, timezone
            await persist_security_event(
                session=session,
                event=SecurityEventCreate(
                    tenant_id=principal.tenant_id,
                    event_type="CONFUSED_DEPUTY_REJECTED",
                    occurred_at=datetime.now(timezone.utc),
                    outcome="FAILURE",
                    agent_id=principal.agent_id,
                    request_id=str(request.request_id),
                    reason_code="delegate_lacks_capability",
                    metadata={
                        "delegation_id": delegation_info.delegation_id,
                        "delegator_agent_id": delegation_info.delegator_agent_id,
                        "delegate_agent_id": principal.agent_id,
                        "requested_action": request.action,
                        "requested_resource": request.resource,
                    },
                ),
                session_factory=session_factory,
                durable=True,
            )

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
            reason=reason,
            delegation_id=request.delegation_id,
            delegator_agent_id=delegation_info.delegator_agent_id if delegation_info else None,
            delegate_agent_id=principal.agent_id if delegation_info else None,
            effective_agent_id=principal.agent_id if delegation_info else None,
            evaluation_ms=0.0,
        )
    elif delegation_info and delegation_info.capability_scope and "*" not in delegation_info.capability_scope and capability_result.capability_id not in delegation_info.capability_scope:
        # Capability intersection failure
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
            reason=DecisionReason.DELEGATION_SCOPE_VIOLATION,
            delegation_id=request.delegation_id,
            delegator_agent_id=delegation_info.delegator_agent_id,
            delegate_agent_id=principal.agent_id,
            effective_agent_id=principal.agent_id,
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

        raw_policy_decision = evaluate_policies(request, policies, principal, capability_id=capability_result.capability_id)
        
        # Populate multi-agent provenance fields
        if delegation_info:
            policy_decision = AuthorizationDecision(
                decision_id=raw_policy_decision.decision_id,
                request_id=raw_policy_decision.request_id,
                tenant_id=raw_policy_decision.tenant_id,
                agent_id=raw_policy_decision.agent_id,
                credential_id=raw_policy_decision.credential_id,
                action=raw_policy_decision.action,
                resource=raw_policy_decision.resource,
                effect=raw_policy_decision.effect,
                reason=raw_policy_decision.reason,
                policy_id=raw_policy_decision.policy_id,
                policy_version_id=raw_policy_decision.policy_version_id,
                risk_assessment_id=raw_policy_decision.risk_assessment_id,
                tool_id=raw_policy_decision.tool_id,
                capability_id=raw_policy_decision.capability_id,
                delegation_id=request.delegation_id,
                delegator_agent_id=delegation_info.delegator_agent_id,
                delegate_agent_id=principal.agent_id,
                effective_agent_id=principal.agent_id,
                evaluated_at=raw_policy_decision.evaluated_at,
                evaluation_ms=raw_policy_decision.evaluation_ms,
            )
        else:
            policy_decision = raw_policy_decision

    # Risk evaluation is always deterministic
    risk_assessment = await evaluate_risk(request, principal, behavior_provider)

    # Combine policy and risk deterministically
    final_decision = combine_policy_and_risk(policy_decision, risk_assessment)

    # Record both risk and decision transactionally
    await record_decision(session, final_decision, risk_assessment, session_factory=session_factory)

    if final_decision.effect == DecisionEffect.DENY:
        from sentinel_core.security_event_service import persist_security_event, SecurityEventCreate
        from datetime import datetime, timezone
        event_type = "POLICY_DENIED"
        if final_decision.reason == DecisionReason.RISK_DENIED:
            event_type = "RISK_DENIED"
        elif final_decision.reason in (DecisionReason.CAPABILITY_DENIED, "capability_denied"):
            event_type = "CAPABILITY_DENIED"
        elif final_decision.reason == DecisionReason.CONFUSED_DEPUTY_DENIED:
            event_type = "CONFUSED_DEPUTY_REJECTED"
        elif final_decision.reason in (DecisionReason.DELEGATION_DENIED, DecisionReason.DELEGATION_NOT_FOUND, DecisionReason.DELEGATION_EXPIRED, DecisionReason.DELEGATION_REVOKED, DecisionReason.DELEGATION_SCOPE_VIOLATION):
            event_type = "DELEGATION_REJECTED"
        elif final_decision.reason == DecisionReason.IMPERSONATION_ATTEMPT:
            event_type = "IMPERSONATION_ATTEMPT"

        await persist_security_event(
            session=session,
            event=SecurityEventCreate(
                tenant_id=principal.tenant_id,
                event_type=event_type,
                occurred_at=datetime.now(timezone.utc),
                outcome="FAILURE",
                agent_id=principal.agent_id,
                credential_id=principal.credential_id,
                tool_id=request.tool_id,
                policy_id=final_decision.policy_id,
                policy_version_id=final_decision.policy_version_id,
                authorization_decision_id=str(final_decision.decision_id),
                request_id=str(request.request_id) if request.request_id else None,
                reason_code=final_decision.reason.value if hasattr(final_decision.reason, "value") else str(final_decision.reason),
                metadata={
                    "delegation_id": final_decision.delegation_id,
                    "delegator_agent_id": final_decision.delegator_agent_id,
                    "delegate_agent_id": final_decision.delegate_agent_id,
                } if final_decision.delegation_id else None,
            ),
            session_factory=session_factory,
            principal=principal,
        )

    return final_decision
