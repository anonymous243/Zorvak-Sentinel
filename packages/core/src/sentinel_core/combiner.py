from sentinel_core.authorization import AuthorizationDecision, DecisionEffect, DecisionReason
from sentinel_core.risk import RiskAssessment, RiskEvaluationStatus, RiskLevel

def combine_policy_and_risk(
    policy_decision: AuthorizationDecision,
    risk_assessment: RiskAssessment,
) -> AuthorizationDecision:
    """
    Deterministically combines a policy decision and a risk assessment into a final decision.
    
    POLICY DENY + any risk result => FINAL DENY
    POLICY ALLOW + LOW          => FINAL ALLOW
    POLICY ALLOW + MEDIUM       => FINAL ALLOW
    POLICY ALLOW + HIGH         => FINAL ALLOW
    POLICY ALLOW + CRITICAL     => FINAL DENY with reason RISK_DENIED
    POLICY ALLOW + risk UNKNOWN => FINAL DENY with reason RISK_EVALUATION_ERROR
    POLICY ALLOW + risk ERROR   => FINAL DENY with reason RISK_EVALUATION_ERROR
    """
    
    if policy_decision.effect == DecisionEffect.DENY:
        return policy_decision.model_copy(update={"risk_assessment_id": risk_assessment.id})
        
    if risk_assessment.status in (RiskEvaluationStatus.UNKNOWN, RiskEvaluationStatus.ERROR):
        return policy_decision.model_copy(update={
            "effect": DecisionEffect.DENY,
            "reason": DecisionReason.RISK_EVALUATION_ERROR,
            "risk_assessment_id": risk_assessment.id,
        })
        
    if risk_assessment.level == RiskLevel.CRITICAL:
        return policy_decision.model_copy(update={
            "effect": DecisionEffect.DENY,
            "reason": DecisionReason.RISK_DENIED,
            "risk_assessment_id": risk_assessment.id,
        })
        
    # LOW, MEDIUM, HIGH are allowed
    return policy_decision.model_copy(update={"risk_assessment_id": risk_assessment.id})
