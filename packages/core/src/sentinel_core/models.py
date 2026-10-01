from datetime import datetime, timezone, date
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Date, Enum, Index, String, Text, ForeignKey, UniqueConstraint, ForeignKeyConstraint, text, Integer, Boolean, JSON, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    slug: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class Membership(Base):
    __tablename__ = "memberships"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "tenant_id",
            name="uq_memberships_user_tenant",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        Enum("OWNER", "ADMIN", "SECURITY", "DEVELOPER", "VIEWER", name="membership_role"),
        nullable=False,
        default="VIEWER",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
    )


    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    provider: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
    )

    environment: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="development",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AgentSecurityDomain(Base):
    __tablename__ = "agent_security_domains"

    __table_args__ = (
        Index("ix_agent_security_domains_tenant", "tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uix_tenant_domain_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AgentSecurityDomainMembership(Base):
    __tablename__ = "agent_security_domain_memberships"

    __table_args__ = (
        Index("ix_agent_security_domain_memberships_domain", "domain_id"),
        Index("ix_agent_security_domain_memberships_agent", "agent_id"),
        UniqueConstraint("domain_id", "agent_id", name="uix_domain_agent"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
    )

    domain_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_security_domains.id"),
        nullable=False,
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AgentCredential(Base):
    __tablename__ = "agent_credentials"

    __table_args__ = (
        Index("ix_agent_credentials_agent_id", "agent_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,
    )

    secret_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        Enum("active", "revoked", name="credential_status"),
        nullable=False,
        default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AgentSigningKey(Base):
    __tablename__ = "agent_signing_keys"

    __table_args__ = (
        Index(
            "ix_agent_signing_keys_agent_id",
            "agent_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,
    )

    public_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        Enum("active", "revoked", name="signing_key_status"),
        nullable=False,
        default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class Capability(Base):
    __tablename__ = "capabilities"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_capabilities_tenant_name",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class Tool(Base):
    __tablename__ = "tools"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_tools_tenant_name",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ToolActionCapability(Base):
    __tablename__ = "tool_action_capabilities"

    __table_args__ = (
        UniqueConstraint(
            "tool_id",
            "action",
            name="uq_tool_action_capabilities_tool_action",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tool_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tools.id"),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    capability_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("capabilities.id"),
        nullable=False,
    )


class AgentCapability(Base):
    __tablename__ = "agent_capabilities"

    __table_args__ = (
        Index(
            "ix_agent_capabilities_agent_id",
            "agent_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,
    )

    capability_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("capabilities.id"),
        nullable=False,
    )

    resource_scope: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="*",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class RiskAssessmentRecord(Base):
    __tablename__ = "risk_assessments"

    __table_args__ = (
        Index(
            "ix_risk_assessments_request_id",
            "request_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    request_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    credential_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    score: Mapped[int] = mapped_column(
        nullable=False,
    )

    level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    factors: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    evaluation_ms: Mapped[float] = mapped_column(
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class AuthorizationDecisionRecord(Base):
    __tablename__ = "authorization_decisions"

    __table_args__ = (
        Index(
            "ix_authorization_decisions_request_id",
            "request_id",
        ),
        Index(
            "ix_authorization_decisions_agent_id_evaluated_at",
            "agent_id",
            "evaluated_at",
        ),
        Index(
            "ix_authorization_decisions_evaluated_at",
            "evaluated_at",
        ),
        Index(
            "ix_authorization_decisions_policy_version_id",
            "policy_version_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    request_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    credential_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    resource: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    effect: Mapped[str] = mapped_column(
        Enum("allow", "deny", name="decision_effect"),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    policy_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    policy_version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("policy_versions.id"),
        nullable=True,
    )

    risk_assessment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("risk_assessments.id"),
        nullable=True,
    )

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    evaluation_ms: Mapped[float] = mapped_column(
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class ExecutionRecord(Base):
    __tablename__ = "executions"

    __table_args__ = (
        Index(
            "ix_executions_request_id",
            "request_id",
        ),
        Index(
            "ix_executions_authorization_decision_id",
            "authorization_decision_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "request_id",
            name="uq_executions_tenant_request",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    request_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    request_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default="",
    )

    authorization_decision_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("authorization_decisions.id"),
        nullable=False,
    )

    risk_assessment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("risk_assessments.id"),
        nullable=True,
    )

    policy_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    policy_version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("policy_versions.id"),
        nullable=True,
    )

    tool_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tools.id"),
        nullable=True,
    )

    capability_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("capabilities.id"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    resource: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ExecutionReconciliation(Base):
    __tablename__ = "execution_reconciliations"

    __table_args__ = (
        Index(
            "ix_execution_reconciliations_execution_id",
            "execution_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("executions.id"),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    reconciler_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    result: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    metadata_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    error_info: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    __table_args__ = (
        CheckConstraint(
            "effect IN ('allow', 'deny')",
            name="ck_policy_versions_effect",
        ),
        UniqueConstraint(
            "policy_id",
            "version",
            name="uq_policy_versions_policy_id_version",
        ),
        UniqueConstraint(
            "policy_id",
            "id",
            name="uq_policy_versions_policy_id_id",
        ),
        Index(
            "ix_policy_versions_single_active",
            "policy_id",
            sqlite_where=text("status = 'active'"),
            postgresql_where=text("status = 'active'"),
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
    )

    policy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("policies.id"),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        nullable=False,
    )

    effect: Mapped[str] = mapped_column(
        Enum("allow", "deny", name="policy_effect"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        Enum("draft", "review", "approved", "published", "active", "deprecated", name="policy_version_status"),
        nullable=False,
        default="draft",
    )

    priority: Mapped[int] = mapped_column(
        nullable=False,
        default=100,
    )

    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    resource: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class Policy(Base):
    __tablename__ = "policies"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_policies_tenant_name",
        ),
        ForeignKeyConstraint(
            ["id", "active_version_id"],
            ["policy_versions.policy_id", "policy_versions.id"],
            name="fk_policy_active_version_composite",
            use_alter=True,
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    active_version_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    enabled: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    active_version: Mapped["PolicyVersion"] = relationship(
        foreign_keys=[active_version_id],
        post_update=True,
    )

    @property
    def effect(self) -> str:
        return self.active_version.effect if self.active_version else None

    @property
    def priority(self) -> int:
        return self.active_version.priority if self.active_version else 100

    @property
    def action(self) -> str:
        return self.active_version.action if self.active_version else ""

    @property
    def resource(self) -> str:
        return self.active_version.resource if self.active_version else ""

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    __table_args__ = (
        Index(
            "ix_outbox_events_status_available_at",
            "status",
            "available_at",
        ),
        Index(
            "ix_outbox_events_correlation_id",
            "correlation_id",
        ),
        Index(
            "ix_outbox_events_processing_lease",
            "status",
            "lease_until",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    event_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    aggregate_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    aggregate_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "processing",
            "published",
            "failed",
            "dead_letter",
            name="outbox_status",
        ),
        nullable=False,
        default="pending",
    )

    attempts: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    claim_token: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

class PolicyAuditRecord(Base):
    __tablename__ = "policy_audit_records"

    __table_args__ = (
        Index(
            "ix_policy_audit_tenant_id",
            "tenant_id",
        ),
        Index(
            "ix_policy_audit_policy_id",
            "policy_id",
        ),
        Index(
            "ix_policy_audit_policy_version_id",
            "policy_version_id",
        ),
        Index(
            "ix_policy_audit_occurred_at",
            "occurred_at",
        ),
        Index(
            "ix_policy_audit_correlation_id",
            "correlation_id",
        ),
        Index(
            "ix_policy_audit_request_id",
            "request_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    policy_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    policy_version_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    credential_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    operation: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    before_state: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    after_state: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

class SecurityEvent(Base):
    __tablename__ = "security_events"

    __table_args__ = (
        Index("ix_security_events_tenant_type_time", "tenant_id", "event_type", "occurred_at"),
        Index("ix_security_events_tenant_agent_time", "tenant_id", "agent_id", "occurred_at"),
        Index("ix_security_events_tenant_correlation", "tenant_id", "correlation_id"),
        Index("ix_security_events_request", "request_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    credential_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tool_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    policy_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    execution_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    authorization_decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))



class Incident(Base):
    __tablename__ = "incidents"

    __table_args__ = (
        Index("ix_incidents_tenant_status", "tenant_id", "status"),
        Index("ix_incidents_tenant_rule_created", "tenant_id", "detection_rule_id", "created_at"),
        # Partial unique index: only one OPEN incident per logical (tenant, rule, agent) triple.
        # Both SQLite and PostgreSQL support WHERE-clause partial indexes via SQLAlchemy text().
        Index(
            "uix_incidents_dedup_key_open",
            "dedup_key",
            unique=True,
            sqlite_where=text("status = 'OPEN'"),
            postgresql_where=text("status = 'OPEN'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    detection_rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Deterministic deduplication key: SHA-256("v1:INCIDENT_DEDUP:<tenant_id>:<rule_id>:<agent_id|''>")
    # Enables the database-level partial unique index to prevent concurrent duplicate incidents.
    dedup_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class IncidentAuditRecord(Base):
    __tablename__ = "incident_audit_records"

    __table_args__ = (
        Index("ix_incident_audit_tenant", "tenant_id"),
        Index("ix_incident_audit_incident", "incident_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    before_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    __table_args__ = (
        Index("ix_alerts_tenant_status", "tenant_id", "status"),
        Index(
            "uix_alerts_incident_open",
            "incident_id",
            unique=True,
            sqlite_where=text("status = 'OPEN'"),
            postgresql_where=text("status = 'OPEN'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AlertAuditRecord(Base):
    __tablename__ = "alert_audit_records"

    __table_args__ = (
        Index("ix_alert_audit_tenant", "tenant_id"),
        Index("ix_alert_audit_alert", "alert_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    alert_id: Mapped[str] = mapped_column(String(36), ForeignKey("alerts.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Evidence(Base):
    __tablename__ = "evidence"

    __table_args__ = (
        Index("ix_evidence_tenant_type", "tenant_id", "evidence_type"),
        Index("ix_evidence_incident", "incident_id"),
        Index("ix_evidence_alert", "alert_id"),
        UniqueConstraint(
            "tenant_id", "evidence_type", "source_type", "source_id", "incident_id",
            name="uq_evidence_identity"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    incident_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=True)
    alert_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("alerts.id"), nullable=True)
    
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_payload: Mapped[str | None] = mapped_column(Text, nullable=True) # JSON stored as Text
    integrity_digest: Mapped[str | None] = mapped_column(String(64), nullable=True) # SHA-256
    
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Investigation(Base):
    __tablename__ = "investigations"

    __table_args__ = (
        Index("ix_investigations_tenant_status", "tenant_id", "status"),
        Index(
            "uix_investigations_incident_active",
            "incident_id",
            unique=True,
            sqlite_where=text("status != 'CLOSED' AND status != 'RESOLVED'"),
            postgresql_where=text("status != 'CLOSED' AND status != 'RESOLVED'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=False)
    alert_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("alerts.id"), nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN") # OPEN, IN_PROGRESS, CONTAINED, RESOLVED, CLOSED
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MEDIUM")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    assigned_to: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Legacy fields to preserve if existing
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    head_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class InvestigationNote(Base):
    __tablename__ = "investigation_notes"
    
    __table_args__ = (
        Index("ix_inv_notes_tenant_inv", "tenant_id", "investigation_id"),
    )
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

class InvestigationFinding(Base):
    __tablename__ = "investigation_findings"
    
    __table_args__ = (
        Index("ix_inv_findings_tenant_inv", "tenant_id", "investigation_id"),
    )
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class InvestigationAuditRecord(Base):
    __tablename__ = "investigation_audit_records"

    __table_args__ = (
        Index("ix_inv_audit_tenant", "tenant_id"),
        Index("ix_inv_audit_inv", "investigation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

class EvidenceLedgerRecord(Base):
    __tablename__ = "evidence_ledger_records"

    __table_args__ = (
        Index("ix_evidence_ledger_tenant", "tenant_id"),
        UniqueConstraint("investigation_id", "seq_num", name="uq_evidence_ledger_seq"),
        UniqueConstraint("investigation_id", "previous_hash", name="uq_evidence_ledger_prev_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    seq_num: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False) # e.g., 'INCIDENT', 'SECURITY_EVENT'
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entity_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    added_by: Mapped[str] = mapped_column(String(128), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class DailyAgentSecurityMetric(Base):
    __tablename__ = "daily_agent_security_metrics"

    __table_args__ = (
        UniqueConstraint("tenant_id", "agent_id", "metric_date", name="uq_daily_agent_metric"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(36), nullable=False)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    policy_denials: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    capability_denials: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_risks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incidents_triggered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class DailyTenantSecurityMetric(Base):
    __tablename__ = "daily_tenant_security_metrics"

    __table_args__ = (
        UniqueConstraint("tenant_id", "metric_date", name="uq_daily_tenant_metric"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_incidents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_investigations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_agents_flagged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class RemediationPlaybook(Base):
    __tablename__ = "remediation_playbooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_severity: Mapped[str] = mapped_column(String(50), nullable=False)
    action_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class AutonomousActionLog(Base):
    __tablename__ = "autonomous_action_logs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    previous_state_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    action_signature: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ExternalIdentityProvider(Base):
    __tablename__ = "external_identity_providers"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "OIDC", "OAUTH"
    issuer_url: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class AgentFederatedIdentity(Base):
    __tablename__ = "agent_federated_identities"
    
    __table_args__ = (
        UniqueConstraint("provider_id", "subject_id", name="uq_agent_federated_identities_provider_subject"),
    )
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("external_identity_providers.id"), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EngineNode(Base):
    __tablename__ = "engine_nodes"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    public_key: Mapped[str] = mapped_column(String(1024), nullable=False)  # Ephemeral public key
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class CryptographicLease(Base):
    __tablename__ = "cryptographic_leases"
    
    resource_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    owner_node_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("engine_nodes.id"), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cryptographic_proof: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class AIAgentAttestation(Base):
    """
    Software Agent Attestation model.
    
    Proves Ed25519 signature verification over a claimed agent/model payload.
    Does NOT prove hardware TEE execution, enclave isolation, secure boot,
    or runtime model memory integrity.
    """
    __tablename__ = "ai_agent_attestations"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, unique=True)
    model_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # Claimed model hash
    tee_signature: Mapped[str] = mapped_column(String(1024), nullable=False)  # Software Ed25519 signature hex (legacy DB column name)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def attestation_type(self) -> str:
        return "software_signed"

    @property
    def claimed_model_hash(self) -> str:
        return self.model_hash

    @property
    def software_signature(self) -> str:
        return self.tee_signature

    @property
    def hardware_attestation(self) -> bool:
        return False

    @property
    def hardware_attestation_verified(self) -> bool:
        return False

    def to_verification_result(self) -> dict:
        return {
            "attestation_type": "software_signed",
            "signature_valid": True,
            "signing_key_verified": True,
            "agent_id": self.agent_id,
            "claimed_model_hash": self.model_hash,
            "hardware_attestation": False,
            "hardware_attestation_verified": False,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }



class AIActionVelocityState(Base):
    __tablename__ = "ai_action_velocity_states"
    
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), primary_key=True)
    tokens: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    last_refill: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    locked_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AIPendingHighRiskAction(Base):
    __tablename__ = "ai_pending_high_risk_actions"
    
    __table_args__ = (
        CheckConstraint(
            "required_signatures >= 1",
            name="ck_ai_pending_high_risk_actions_required_signatures",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    action_payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON payload
    required_signatures: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    collected_signatures: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON array of signatures
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, executed, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)







class RequestReplayRecord(Base):
    __tablename__ = "request_replay_records"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "request_id",
            name="uq_request_replay_records_tenant_request",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    request_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class AgentTrustRelationship(Base):
    __tablename__ = "agent_trust_relationships"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_agent_id",
            "target_agent_id",
            name="uq_agent_trust_tenant_source_target",
        ),
        CheckConstraint(
            "source_agent_id != target_agent_id",
            name="ck_agent_trust_no_self_trust",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'REVOKED', 'EXPIRED')",
            name="ck_agent_trust_status_valid",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    target_agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
    )

    trust_scope: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    meta_data: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class AgentDelegation(Base):
    __tablename__ = "agent_delegations"

    __table_args__ = (
        CheckConstraint(
            "delegator_agent_id != delegate_agent_id",
            name="ck_agent_delegation_no_self_delegation",
        ),
        CheckConstraint(
            "expires_at > issued_at",
            name="ck_agent_delegation_expires_after_issued",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'REVOKED', 'EXPIRED')",
            name="ck_agent_delegation_status_valid",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    delegator_agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    delegate_agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    trust_relationship_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_trust_relationships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    action_scope: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    resource_scope: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    capability_scope: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    parent_delegation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("agent_delegations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
    )

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    signature: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    signing_key_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_signing_keys.id"),
        nullable=False,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    meta_data: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

