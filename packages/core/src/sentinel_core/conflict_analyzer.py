from typing import List, Tuple
from sentinel_core.models import PolicyVersion, Policy
from sentinel_core.schemas import ConflictReport, ConflictType, PatternRelationship
from sentinel_core.authorization import DecisionEffect

def analyze_pattern_relationship(pattern_a: str, pattern_b: str) -> PatternRelationship:
    """
    Analyzes the deterministic relationship between two action/resource patterns.
    Supports exact match, prefix:*, and total wildcard *.
    """
    if pattern_a == pattern_b:
        return PatternRelationship.EQUAL

    if pattern_a == "*":
        return PatternRelationship.A_SUBSUMES_B

    if pattern_b == "*":
        return PatternRelationship.B_SUBSUMES_A

    # Prefix match logic
    a_is_prefix = pattern_a.endswith("*")
    b_is_prefix = pattern_b.endswith("*")

    if a_is_prefix and b_is_prefix:
        prefix_a = pattern_a[:-1]
        prefix_b = pattern_b[:-1]
        if prefix_b.startswith(prefix_a):
            return PatternRelationship.A_SUBSUMES_B
        if prefix_a.startswith(prefix_b):
            return PatternRelationship.B_SUBSUMES_A
        return PatternRelationship.DISJOINT

    if a_is_prefix:
        prefix_a = pattern_a[:-1]
        if pattern_b.startswith(prefix_a):
            return PatternRelationship.A_SUBSUMES_B
        return PatternRelationship.DISJOINT

    if b_is_prefix:
        prefix_b = pattern_b[:-1]
        if pattern_a.startswith(prefix_b):
            return PatternRelationship.B_SUBSUMES_A
        return PatternRelationship.DISJOINT

    return PatternRelationship.DISJOINT


def analyze_scope_subsumption(
    action_rel: PatternRelationship, resource_rel: PatternRelationship
) -> PatternRelationship:
    """
    Determines the overall scope relationship.
    A fully subsumes B if A subsumes B on both dimensions (or one is equal).
    """
    if action_rel == PatternRelationship.DISJOINT or resource_rel == PatternRelationship.DISJOINT:
        return PatternRelationship.DISJOINT

    if action_rel == PatternRelationship.EQUAL and resource_rel == PatternRelationship.EQUAL:
        return PatternRelationship.EQUAL

    a_covers_action = action_rel in (PatternRelationship.EQUAL, PatternRelationship.A_SUBSUMES_B)
    a_covers_resource = resource_rel in (PatternRelationship.EQUAL, PatternRelationship.A_SUBSUMES_B)
    if a_covers_action and a_covers_resource:
        return PatternRelationship.A_SUBSUMES_B

    b_covers_action = action_rel in (PatternRelationship.EQUAL, PatternRelationship.B_SUBSUMES_A)
    b_covers_resource = resource_rel in (PatternRelationship.EQUAL, PatternRelationship.B_SUBSUMES_A)
    if b_covers_action and b_covers_resource:
        return PatternRelationship.B_SUBSUMES_A

    return PatternRelationship.OVERLAPPING


def _specificity(pattern: str) -> int:
    if pattern == "*":
        return 0
    if pattern.endswith("*"):
        return len(pattern) - 1
    return 1000 + len(pattern)


def compare_precedence(a_version: PolicyVersion, b_version: PolicyVersion) -> int:
    """
    Returns >0 if A wins, <0 if B wins, 0 if tied (should not happen due to policy ID).
    Matches decision_engine.py precedence precisely:
    1. priority descending
    2. specificity descending
    3. DENY before ALLOW
    4. policy_id ascending
    """
    if a_version.priority != b_version.priority:
        return a_version.priority - b_version.priority

    a_spec = _specificity(a_version.action) + _specificity(a_version.resource)
    b_spec = _specificity(b_version.action) + _specificity(b_version.resource)
    if a_spec != b_spec:
        return a_spec - b_spec

    # Deny before allow (0 for DENY, 1 for ALLOW in sorted key, so DENY > ALLOW here)
    if a_version.effect != b_version.effect:
        return 1 if a_version.effect == DecisionEffect.DENY else -1

    # Ascending policy ID means smaller string wins, so if A is smaller, A wins (positive value)
    if a_version.policy_id < b_version.policy_id:
        return 1
    elif a_version.policy_id > b_version.policy_id:
        return -1

    return 0


def analyze_conflicts(
    target: PolicyVersion, active_versions: List[PolicyVersion]
) -> List[ConflictReport]:
    """
    Analyzes conflicts between a target PolicyVersion and a list of active PolicyVersions.
    Fails closed if there are tenant mismatches or invalid status.
    """
    if not target.tenant_id or not target.policy_id:
        raise ValueError("Target policy version missing tenant_id or policy_id")

    reports: List[ConflictReport] = []

    for active in active_versions:
        if active.tenant_id != target.tenant_id:
            raise ValueError("Tenant mismatch in active version")
        if not active.policy_id:
            raise ValueError("Active version missing policy_id")
        if active.status != "active":
            raise ValueError("Comparison set must contain only active versions")

        if active.id == target.id:
            continue

        action_rel = analyze_pattern_relationship(target.action, active.action)
        resource_rel = analyze_pattern_relationship(target.resource, active.resource)

        scope_rel = analyze_scope_subsumption(action_rel, resource_rel)

        if scope_rel == PatternRelationship.DISJOINT:
            continue

        target_wins = compare_precedence(target, active) > 0
        same_effect = target.effect == active.effect

        conflict_type = None
        explanation = ""

        # Shadowed Logic
        target_shadowed = scope_rel in (PatternRelationship.B_SUBSUMES_A, PatternRelationship.EQUAL) and not target_wins
        
        if same_effect and scope_rel in (PatternRelationship.B_SUBSUMES_A, PatternRelationship.EQUAL):
            conflict_type = ConflictType.REDUNDANT
            explanation = "TARGET_REDUNDANT_SAME_EFFECT"
        elif target_shadowed:
            conflict_type = ConflictType.SHADOWED
            explanation = "TARGET_FULLY_SHADOWED_BY_HIGHER_PRIORITY_RULE"
        elif not same_effect:
            # Different effects
            if scope_rel == PatternRelationship.EQUAL:
                conflict_type = ConflictType.CONTRADICTION
                explanation = "SAME_SCOPE_OPPOSING_EFFECTS"
            elif scope_rel == PatternRelationship.OVERLAPPING:
                conflict_type = ConflictType.CONTRADICTION
                explanation = "PARTIAL_SCOPE_OPPOSING_EFFECTS"
            else:
                # A_SUBSUMES_B or B_SUBSUMES_A
                conflict_type = ConflictType.OVERLAP
                explanation = "HIGHER_PRIORITY_OVERRIDE" if target_wins else "PARTIAL_SCOPE_OVERLAP"
        else:
            # Same effect, but not redundant (e.g. A_SUBSUMES_B or OVERLAPPING)
            conflict_type = ConflictType.OVERLAP
            explanation = "HIGHER_PRIORITY_OVERRIDE" if target_wins else "PARTIAL_SCOPE_OVERLAP"

        reports.append(
            ConflictReport(
                conflict_type=conflict_type,
                target_policy_id=target.policy_id,
                target_policy_version_id=target.id,
                conflicting_policy_id=active.policy_id,
                conflicting_policy_version_id=active.id,
                relationship=scope_rel,
                target_effect=target.effect,
                conflicting_effect=active.effect,
                target_priority=target.priority,
                conflicting_priority=active.priority,
                explanation_code=explanation,
            )
        )

    # Sort reports deterministically
    reports.sort(
        key=lambda r: (
            r.conflict_type.value,
            r.conflicting_policy_id,
            r.conflicting_policy_version_id,
        )
    )

    return reports
