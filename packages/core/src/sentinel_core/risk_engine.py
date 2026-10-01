from datetime import datetime, timezone
from time import perf_counter
from typing import List, Mapping

from sentinel_core.authorization import ActionRequest, AuthorizationDecision
from sentinel_core.principals import AuthenticatedPrincipal
from sentinel_core.risk import (
    BehaviorSignalProvider,
    RiskAssessment,
    RiskEvaluationStatus,
    RiskFactor,
    RiskLevel,
)

# Explicit scoring weights
SENSITIVE_ACTION_SCORE = 30
SENSITIVE_RESOURCE_SCORE = 40
ANOMALOUS_CONTEXT_SCORE = 20
BEHAVIORAL_DEVIATION_SCORE = 30

# We can define a set of known sensitive actions/resources for deterministic evaluation.
# In a real system, these might come from configuration or a database.
KNOWN_SENSITIVE_ACTIONS = {"delete", "grant", "revoke", "export"}
KNOWN_SENSITIVE_RESOURCES = {"secrets", "billing", "audit_logs", "iam"}

def _is_sensitive_action(action: str) -> bool:
    # Basic deterministic check
    action_lower = action.lower()
    return any(sens in action_lower for sens in KNOWN_SENSITIVE_ACTIONS)

def _is_sensitive_resource(resource: str) -> bool:
    # Basic deterministic check
    resource_lower = resource.lower()
    return any(sens in resource_lower for sens in KNOWN_SENSITIVE_RESOURCES)

def _has_anomalous_context(context: Mapping[str, str]) -> bool:
    # Explicitly supplied contextual anomaly indicators
    return context.get("anomalous") == "true" or context.get("risk_indicator") == "high"

def _has_behavioral_deviation(context: Mapping[str, str]) -> bool:
    return (
        context.get("behavioral_deviation") == "true"
        or context.get("deviation") == "true"
        or context.get("unusual_pattern") == "true"
    )


def _map_score_to_level(score: int) -> RiskLevel:
    """
    Map score to risk level deterministically.
    0-24   LOW
    25-49  MEDIUM
    50-74  HIGH
    75-100 CRITICAL
    """
    if score <= 24:
        return RiskLevel.LOW
    elif score <= 49:
        return RiskLevel.MEDIUM
    elif score <= 74:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


async def evaluate_risk(
    request: ActionRequest,
    principal: AuthenticatedPrincipal,
    behavior_provider: BehaviorSignalProvider,
) -> RiskAssessment:
    """
    Evaluates the risk of an action deterministically.
    """
    started = perf_counter()
    score = 0
    factors: List[RiskFactor] = []
    
    try:
        if _is_sensitive_action(request.action):
            score += SENSITIVE_ACTION_SCORE
            factors.append(RiskFactor.SENSITIVE_ACTION)
            
        if _is_sensitive_resource(request.resource):
            score += SENSITIVE_RESOURCE_SCORE
            factors.append(RiskFactor.SENSITIVE_RESOURCE)
            
        if _has_anomalous_context(request.context):
            score += ANOMALOUS_CONTEXT_SCORE
            factors.append(RiskFactor.ANOMALOUS_CONTEXT)

        if _has_behavioral_deviation(request.context) and RiskFactor.BEHAVIORAL_DEVIATION not in factors:
            score += BEHAVIORAL_DEVIATION_SCORE
            factors.append(RiskFactor.BEHAVIORAL_DEVIATION)

        # Get behavioral signals
        signals = await behavior_provider.get_signals(
            tenant_id=principal.tenant_id,
            agent_id=principal.agent_id,
            action=request.action,
            resource=request.resource,
        )
        
        for signal in signals:
            score += signal.score_contribution
            if signal.factor not in factors:
                factors.append(signal.factor)
                
        # Clamp score to 0..100
        clamped_score = max(0, min(100, score))
        
        level = _map_score_to_level(clamped_score)
        
        return RiskAssessment(
            tenant_id=principal.tenant_id,
            agent_id=principal.agent_id,
            request_id=request.request_id,
            credential_id=principal.credential_id,
            score=clamped_score,
            level=level,
            factors=factors,
            status=RiskEvaluationStatus.SUCCESS,
            evaluation_ms=(perf_counter() - started) * 1000,
        )
        
    except Exception:
        # Fail closed/UNKNOWN on error
        return RiskAssessment(
            tenant_id=principal.tenant_id,
            agent_id=principal.agent_id,
            request_id=request.request_id,
            credential_id=principal.credential_id,
            score=100,
            level=RiskLevel.CRITICAL,
            factors=[],
            status=RiskEvaluationStatus.ERROR,
            evaluation_ms=(perf_counter() - started) * 1000,
        )
