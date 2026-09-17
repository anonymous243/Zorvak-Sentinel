from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import List

from sentinel_core.models import Policy, PolicyVersion

class PolicyValidationErrorCode(StrEnum):
    MISSING_POLICY_ID = "missing_policy_id"
    MISSING_TENANT_ID = "missing_tenant_id"
    TENANT_MISMATCH = "tenant_mismatch"
    EMPTY_ACTION = "empty_action"
    EMPTY_RESOURCE = "empty_resource"
    INVALID_WILDCARD = "invalid_wildcard"
    INVALID_EFFECT = "invalid_effect"
    INVALID_PRIORITY = "invalid_priority"
    INVALID_STATUS = "invalid_status"
    INVALID_ACTIVE_VERSION_REF = "invalid_active_version_ref"


@dataclass(frozen=True)
class PolicyValidationError:
    code: PolicyValidationErrorCode
    message: str
    field: str | None = None


@dataclass(frozen=True)
class PolicyValidationResult:
    valid: bool
    errors: list[PolicyValidationError]


def _validate_pattern(pattern: str, field: str, errors: List[PolicyValidationError]) -> None:
    if not pattern:
        errors.append(PolicyValidationError(
            code=PolicyValidationErrorCode.EMPTY_ACTION if field == "action" else PolicyValidationErrorCode.EMPTY_RESOURCE,
            message=f"{field} must not be empty",
            field=field,
        ))
        return

    # Check for invalid wildcard usage.
    # Allowed: 
    #   "*"
    #   "prefix*"
    #   "exact"
    if "*" in pattern:
        if pattern == "*":
            return
        if not pattern.endswith("*"):
            errors.append(PolicyValidationError(
                code=PolicyValidationErrorCode.INVALID_WILDCARD,
                message=f"Wildcard '*' may only appear at the end of the {field}",
                field=field,
            ))
            return
        # If it ends with *, ensure there's only one
        if pattern.count("*") > 1:
            errors.append(PolicyValidationError(
                code=PolicyValidationErrorCode.INVALID_WILDCARD,
                message=f"Multiple wildcards '*' are not permitted in {field}",
                field=field,
            ))
            return


def validate_policy_version(version: PolicyVersion, policy: Policy | None = None) -> PolicyValidationResult:
    """
    Validate a PolicyVersion structurally and semantically without I/O or side effects.
    If 'policy' is provided, cross-validation against the owning policy is performed.
    """
    errors: List[PolicyValidationError] = []

    if not version.policy_id:
        errors.append(PolicyValidationError(
            code=PolicyValidationErrorCode.MISSING_POLICY_ID,
            message="policy_id is required",
            field="policy_id",
        ))

    if not version.tenant_id:
        errors.append(PolicyValidationError(
            code=PolicyValidationErrorCode.MISSING_TENANT_ID,
            message="tenant_id is required",
            field="tenant_id",
        ))

    if policy:
        if version.policy_id != policy.id:
            errors.append(PolicyValidationError(
                code=PolicyValidationErrorCode.MISSING_POLICY_ID,
                message="PolicyVersion belongs to a different Policy",
                field="policy_id",
            ))
        if version.tenant_id != policy.tenant_id:
            errors.append(PolicyValidationError(
                code=PolicyValidationErrorCode.TENANT_MISMATCH,
                message="PolicyVersion tenant_id does not match Policy tenant_id",
                field="tenant_id",
            ))
        
        # If the policy claims this version is active, verify consistency.
        if policy.active_version_id == version.id:
            if version.status != "active":
                errors.append(PolicyValidationError(
                    code=PolicyValidationErrorCode.INVALID_ACTIVE_VERSION_REF,
                    message="Policy marks version as active, but version status is not active",
                    field="status",
                ))
            if policy.active_version and policy.active_version is not version:
                errors.append(PolicyValidationError(
                    code=PolicyValidationErrorCode.INVALID_ACTIVE_VERSION_REF,
                    message="Policy active_version reference mismatch",
                    field="active_version_id",
                ))

    if version.effect not in ("allow", "deny"):
        errors.append(PolicyValidationError(
            code=PolicyValidationErrorCode.INVALID_EFFECT,
            message=f"Invalid effect '{version.effect}'",
            field="effect",
        ))

    # Bounded priority: 0 to 9999
    if not isinstance(version.priority, int) or version.priority < 0 or version.priority > 9999:
        errors.append(PolicyValidationError(
            code=PolicyValidationErrorCode.INVALID_PRIORITY,
            message="Priority must be an integer between 0 and 9999",
            field="priority",
        ))

    # Supported lifecycle statuses
    valid_statuses = {"draft", "review", "approved", "published", "active", "deprecated"}
    if version.status not in valid_statuses:
        errors.append(PolicyValidationError(
            code=PolicyValidationErrorCode.INVALID_STATUS,
            message=f"Invalid status '{version.status}'",
            field="status",
        ))

    _validate_pattern(version.action, "action", errors)
    _validate_pattern(version.resource, "resource", errors)

    # Sort errors deterministically (e.g. by field then code)
    errors.sort(key=lambda e: (e.field or "", e.code))

    return PolicyValidationResult(
        valid=len(errors) == 0,
        errors=errors,
    )
