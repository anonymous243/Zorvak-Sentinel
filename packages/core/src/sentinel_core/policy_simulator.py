import time
from typing import List, Optional

from sentinel_core.authorization import ActionRequest, DecisionEffect, DecisionReason, AuthorizationDecision
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.models import Policy
from sentinel_core.schemas import PolicySimulationResult
from sentinel_core.decision_engine import evaluate_policies
from sentinel_core.combiner import combine_policy_and_risk
from sentinel_core.risk import RiskAssessment


def simulate_authorization(
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    policies: List[Policy],
    agent_status: str | None,
    capability_allowed: bool,
    capability_id: str | None,
    capability_reason: DecisionReason | None,
    risk_assessment: RiskAssessment | None,
    candidate_used: bool = False,
) -> PolicySimulationResult:
    """
    Pure, deterministic simulation core.
    Operates entirely in-memory and produces a PolicySimulationResult.
    Does NOT write to database, execute tools, or dispatch outbox events.
    """
    start_time = time.perf_counter()

    # 1. Identity & Agent Checks
    if request.agent_id != principal.agent_id:
        return PolicySimulationResult(
            effect=DecisionEffect.DENY.value,
            reason="Anti-impersonation failure",
            simulation_ms=(time.perf_counter() - start_time) * 1000,
            candidate_used=candidate_used,
        )

    if agent_status is None:
        return PolicySimulationResult(
            effect=DecisionEffect.DENY.value,
            reason=DecisionReason.AGENT_NOT_FOUND.value,
            simulation_ms=(time.perf_counter() - start_time) * 1000,
            candidate_used=candidate_used,
        )

    if agent_status != "active":
        return PolicySimulationResult(
            effect=DecisionEffect.DENY.value,
            reason=DecisionReason.AGENT_DISABLED.value,
            simulation_ms=(time.perf_counter() - start_time) * 1000,
            candidate_used=candidate_used,
        )

    # 2. Capability Checks
    if not capability_allowed:
        return PolicySimulationResult(
            effect=DecisionEffect.DENY.value,
            reason=capability_reason.value if capability_reason else DecisionReason.CAPABILITY_DENIED.value,
            capability_id=capability_id,
            simulation_ms=(time.perf_counter() - start_time) * 1000,
            candidate_used=candidate_used,
        )

    # 3. Policy Evaluation
    policy_decision = evaluate_policies(
        request=request,
        policies=policies,
        principal=principal,
        capability_id=capability_id,
    )

    # 4. Risk Evaluation
    # Note: risk_assessment is already computed deterministically by the caller and passed in.
    if risk_assessment:
        final_decision = combine_policy_and_risk(policy_decision, risk_assessment)
    else:
        final_decision = policy_decision

    return PolicySimulationResult(
        effect=final_decision.effect.value,
        reason=final_decision.reason.value,
        evaluated_policy_id=final_decision.policy_id,
        evaluated_policy_version_id=final_decision.policy_version_id,
        risk_level=risk_assessment.level.value if risk_assessment else None,
        capability_id=final_decision.capability_id,
        simulation_ms=(time.perf_counter() - start_time) * 1000,
        candidate_used=candidate_used,
    )
