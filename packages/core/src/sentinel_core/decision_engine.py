from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from sentinel_core.authorization import (
    ActionRequest,
    AuthorizationDecision,
    DecisionEffect,
    DecisionReason,
)
from sentinel_core.models import Policy
from sentinel_core.principals import AuthenticatedPrincipal


@dataclass(frozen=True, slots=True)
class PolicyMatch:
    policy: Policy


def _matches_pattern(value: str, pattern: str) -> bool:
    """
    Match a SENTINEL policy pattern.

    Current matching semantics:
      exact value      -> exact match
      prefix:*         -> prefix match
      *                -> wildcard match

    Wildcards are intentionally limited to a trailing '*' so policy
    semantics remain deterministic and cannot accidentally become a
    full glob/regex language.
    """
    if pattern == "*":
        return True

    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])

    return value == pattern


def _policy_matches(
    policy: Policy,
    request: ActionRequest,
) -> bool:
    if not policy.enabled:
        return False

    return (
        _matches_pattern(request.action, policy.action)
        and _matches_pattern(request.resource, policy.resource)
    )


def _specificity(pattern: str) -> int:
    """
    Calculate the deterministic specificity of a pattern.
    - Exact match: 1000 + length
    - Suffix wildcard (prefix:*): length of prefix
    - Total wildcard (*): 0
    """
    if pattern == "*":
        return 0
    if pattern.endswith("*"):
        return len(pattern) - 1
    return 1000 + len(pattern)

def evaluate_policies(
    request: ActionRequest,
    policies: list[Policy],
    principal: AuthenticatedPrincipal,
    capability_id: str | None = None,
) -> AuthorizationDecision:
    """
    Evaluate an authorization request against an already-loaded policy set.

    Security model:
      - Validates all policies for tenant and lifecycle integrity.
      - If ANY policy is invalid, fail closed immediately.
      - Disabled policies are skipped.
    """
    started = perf_counter()

    # Pre-validation: ensure all policies are structurally sound before any matching.
    # We must fail closed if we see ANY invalid policy state, because ignoring it
    # might skip a DENY policy that was supposed to block this action.
    for policy in policies:
        if not policy.enabled:
            continue
            
        if policy.tenant_id != principal.tenant_id:
            return AuthorizationDecision(
                request_id=request.request_id,
                tenant_id=principal.tenant_id,
                agent_id=request.agent_id,
                credential_id=principal.credential_id,
                action=request.action,
                resource=request.resource,
                effect=DecisionEffect.DENY,
                reason=DecisionReason.INVALID_POLICY_STATE,
                tool_id=request.tool_id,
                capability_id=capability_id,
                evaluation_ms=(perf_counter() - started) * 1000,
            )

        if not policy.active_version:
            return AuthorizationDecision(
                request_id=request.request_id,
                tenant_id=principal.tenant_id,
                agent_id=request.agent_id,
                credential_id=principal.credential_id,
                action=request.action,
                resource=request.resource,
                effect=DecisionEffect.DENY,
                reason=DecisionReason.INVALID_POLICY_STATE,
                tool_id=request.tool_id,
                capability_id=capability_id,
                evaluation_ms=(perf_counter() - started) * 1000,
            )
            
        if policy.active_version.tenant_id != policy.tenant_id:
            return AuthorizationDecision(
                request_id=request.request_id,
                tenant_id=principal.tenant_id,
                agent_id=request.agent_id,
                credential_id=principal.credential_id,
                action=request.action,
                resource=request.resource,
                effect=DecisionEffect.DENY,
                reason=DecisionReason.INVALID_POLICY_STATE,
                tool_id=request.tool_id,
                capability_id=capability_id,
                evaluation_ms=(perf_counter() - started) * 1000,
            )
            
        if policy.active_version.status != "active":
            return AuthorizationDecision(
                request_id=request.request_id,
                tenant_id=principal.tenant_id,
                agent_id=request.agent_id,
                credential_id=principal.credential_id,
                action=request.action,
                resource=request.resource,
                effect=DecisionEffect.DENY,
                reason=DecisionReason.INVALID_POLICY_STATE,
                tool_id=request.tool_id,
                capability_id=capability_id,
                evaluation_ms=(perf_counter() - started) * 1000,
            )

    matches = [
        PolicyMatch(policy=policy)
        for policy in policies
        if _policy_matches(policy, request)
    ]

    if matches:
        # Precedence Algorithm:
        # 1. priority (highest wins)
        # 2. specificity score (highest wins)
        # 3. effect (DENY beats ALLOW)
        # 4. policy.id tie-breaker (string sort, arbitrary but deterministic)
        winning_match = sorted(
            matches,
            key=lambda match: (
                -match.policy.priority,
                -(_specificity(match.policy.action) + _specificity(match.policy.resource)),
                0 if match.policy.effect == DecisionEffect.DENY else 1,
                match.policy.id,
            ),
        )[0]

        policy = winning_match.policy

        if policy.effect == DecisionEffect.DENY:
            return AuthorizationDecision(
                request_id=request.request_id,
                tenant_id=principal.tenant_id,
                agent_id=request.agent_id,
                credential_id=principal.credential_id,
                action=request.action,
                resource=request.resource,
                effect=DecisionEffect.DENY,
                reason=DecisionReason.POLICY_DENIED,
                policy_id=policy.id,
                policy_version_id=policy.active_version.id,
                tool_id=request.tool_id,
                capability_id=capability_id,
                evaluation_ms=(perf_counter() - started) * 1000,
            )

        return AuthorizationDecision(
            request_id=request.request_id,
            tenant_id=principal.tenant_id,
            agent_id=request.agent_id,
            credential_id=principal.credential_id,
            action=request.action,
            resource=request.resource,
            effect=DecisionEffect.ALLOW,
            reason=DecisionReason.POLICY_ALLOWED,
            policy_id=policy.id,
            policy_version_id=policy.active_version.id,
            tool_id=request.tool_id,
            capability_id=capability_id,
            evaluation_ms=(perf_counter() - started) * 1000,
        )

    return AuthorizationDecision(
        request_id=request.request_id,
        tenant_id=principal.tenant_id,
        agent_id=request.agent_id,
        credential_id=principal.credential_id,
        action=request.action,
        resource=request.resource,
        effect=DecisionEffect.DENY,
        reason=DecisionReason.NO_MATCHING_POLICY,
        tool_id=request.tool_id,
        capability_id=capability_id,
        evaluation_ms=(perf_counter() - started) * 1000,
    )
