from datetime import datetime, timezone
from enum import StrEnum
from typing import Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from sentinel_core.authorization import ActionRequest
from sentinel_core.principals import AuthenticatedPrincipal


class ExecutionStatus(StrEnum):
    NOT_EXECUTED = "not_executed"
    EXECUTION_PENDING = "execution_pending"
    EXECUTION_STARTED = "execution_started"
    EXECUTED = "executed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_UNKNOWN = "execution_unknown"


class ReconciliationResult(StrEnum):
    DID_EXECUTE = "did_execute"
    DID_NOT_EXECUTE = "did_not_execute"
    STILL_UNKNOWN = "still_unknown"


class ExecutionResult(BaseModel):
    """
    The structured outcome of an action executor.
    """
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )
    
    status: ExecutionStatus
    metadata: Mapping[str, str] = Field(default_factory=dict)
    completed_at: datetime | None = Field(default=None)


class ActionExecutor:
    """
    Abstract base class for action executors.
    The exact executor determines how the action is physically carried out 
    (e.g., HTTP request, local function call, DB operation).
    """

    is_idempotent: bool = False

    async def execute(
        self, request: ActionRequest, principal: AuthenticatedPrincipal
    ) -> ExecutionResult:
        raise NotImplementedError


class ExecutionReconciler:
    """
    Abstract base class for reconciliation.
    Determines if an action actually occurred when its execution state is UNKNOWN.
    """

    async def reconcile(
        self, execution_id: str, request: ActionRequest, principal: AuthenticatedPrincipal
    ) -> tuple[ReconciliationResult, Mapping[str, str]]:
        """
        Query the external system for status.
        MUST NOT re-execute the action.
        Returns the reconciliation result and safe diagnostic metadata.
        """
        raise NotImplementedError


class DeterministicTestExecutor(ActionExecutor):
    """
    A controlled deterministic executor for testing the gateway boundary.
    It returns results based on the presence of special flags in the request context.
    """
    
    async def execute(
        self, request: ActionRequest, principal: AuthenticatedPrincipal
    ) -> ExecutionResult:
        # For testing, we read "test_execution_behavior" from context
        behavior = request.context.get("test_execution_behavior", "success")
        
        if behavior == "success":
            return ExecutionResult(
                status=ExecutionStatus.EXECUTED,
                completed_at=datetime.now(timezone.utc)
            )
        elif behavior == "failure":
            return ExecutionResult(
                status=ExecutionStatus.EXECUTION_FAILED,
                completed_at=datetime.now(timezone.utc),
                metadata={"error": "simulated definite failure"}
            )
        elif behavior == "unknown":
            return ExecutionResult(
                status=ExecutionStatus.EXECUTION_UNKNOWN,
                completed_at=datetime.now(timezone.utc),
                metadata={"error": "simulated uncertain outcome"}
            )
        elif behavior == "exception_pre_dispatch":
            # An exception that proves the external action could not have occurred
            raise ValueError("Pre-dispatch exception")
        else:
            # Ambiguous exception
            raise RuntimeError("Unknown executor failure")
