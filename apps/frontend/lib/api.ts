/**
 * Centralized API client for ZORVAK SENTINEL frontend.
 * Authenticates via HTTP Basic using stored agent credentials.
 * Backend is the authority — no auth logic lives here.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type ApiError = {
  status: number;
  message: string;
};

function getCredentials(): string | null {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem('sentinel_creds');
}

export function saveCredentials(agentId: string, secret: string) {
  const encoded = btoa(`${agentId}:${secret}`);
  sessionStorage.setItem('sentinel_creds', encoded);
  sessionStorage.setItem('sentinel_agent_id', agentId);
  sessionStorage.setItem('sentinel_tenant_id', agentId); // agent_id used as tenant context
}

export function clearCredentials() {
  sessionStorage.removeItem('sentinel_creds');
  sessionStorage.removeItem('sentinel_agent_id');
  sessionStorage.removeItem('sentinel_tenant_id');
}

export function getTenantId(): string {
  if (typeof window === 'undefined') return '';
  return sessionStorage.getItem('sentinel_tenant_id') || '';
}

export function isAuthenticated(): boolean {
  return !!getCredentials();
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false,
  tenantId?: string
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (authenticated) {
    const creds = getCredentials();
    if (!creds) throw { status: 401, message: 'Not authenticated' } as ApiError;
    headers['Authorization'] = `Basic ${creds}`;
    const tid = tenantId || getTenantId();
    if (tid) headers['X-Tenant-ID'] = tid;
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include' // include cookies in requests to the backend
  });

  if (res.status === 401) throw { status: 401, message: 'Authentication failed. Check your credentials.' } as ApiError;
  if (res.status === 403) throw { status: 403, message: 'You do not have permission to perform this action.' } as ApiError;
  if (res.status === 404) throw { status: 404, message: 'Resource not found.' } as ApiError;
  if (res.status === 409) throw { status: 409, message: 'Conflict: This resource was modified by another process. Refresh and retry.' } as ApiError;
  if (res.status === 422) {
    const body = await res.json().catch(() => ({}));
    let msg = 'Validation error.';
    if (typeof body?.detail === 'string') {
      msg = body.detail;
    } else if (Array.isArray(body?.detail)) {
      msg = body.detail.map((e: any) => e.msg).join(', ');
    }
    throw { status: 422, message: msg } as ApiError;
  }
  if (!res.ok) {
    throw { status: res.status, message: 'An unexpected error occurred. Please try again.' } as ApiError;
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Health ──────────────────────────────────────────────────────────────────
export const health = () => request<{ status: string }>('/health');

// ── Auth ──────────────────────────────────────────────────────────────────
export const login = (data: any) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) });
export const signup = (data: any) => request('/auth/signup', { method: 'POST', body: JSON.stringify(data) });
export const logout = () => request('/auth/logout', { method: 'POST' });
export const getMe = () => request('/auth/me');

// ── Agents ──────────────────────────────────────────────────────────────────
export type Agent = {
  id: string;
  name: string;
  description: string | null;
  provider: string | null;
  external_id: string | null;
  status: string;
  environment: string;
  created_at: string;
  updated_at: string;
};

export type AgentCreate = {
  name: string;
  description?: string;
  environment?: string;
  provider?: string;
};

export const listAgents = () => request<Agent[]>('/agents');
export const getAgent = (id: string) => request<Agent>(`/agents/${id}`);
export const createAgent = (data: AgentCreate) =>
  request<Agent>('/agents', { method: 'POST', body: JSON.stringify(data) });

// ── Policies ─────────────────────────────────────────────────────────────────
export type Policy = {
  id: string;
  name: string;
  description: string | null;
  effect: 'allow' | 'deny';
  priority: number;
  action: string;
  resource: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type PolicyCreate = {
  name: string;
  description?: string;
  effect: 'allow' | 'deny';
  priority?: number;
  action: string;
  resource: string;
};

export const listPolicies = () => request<Policy[]>('/policies');

export const createPolicy = (data: PolicyCreate, tenantId: string) =>
  request<Policy>('/policies', { method: 'POST', body: JSON.stringify(data) }, true, tenantId);

export type SimulationRequest = {
  agent_id: string;
  tool_id: string;
  action: string;
  resource: string;
  context?: Record<string, string>;
  candidate_policy_version_id?: string;
};

export type SimulationResult = {
  effect: string;
  reason: string;
  evaluated_policy_id: string | null;
  evaluated_policy_version_id: string | null;
  risk_level: string | null;
  capability_id: string | null;
  simulation_ms: number;
  candidate_used: boolean;
};

export const simulatePolicy = (data: SimulationRequest, tenantId: string) =>
  request<SimulationResult>('/policies/simulate', { method: 'POST', body: JSON.stringify(data) }, true, tenantId);

export type RollbackRequest = { target_version_id: string };
export type RollbackResult = {
  policy_id: string;
  previous_active_version_id: string | null;
  new_active_version_id: string;
  changed: boolean;
  reason: string;
};

export const rollbackPolicy = (policyId: string, data: RollbackRequest, tenantId: string) =>
  request<RollbackResult>(`/policies/${policyId}/rollback`, { method: 'POST', body: JSON.stringify(data) }, true, tenantId);

export type AuditRecord = {
  id: string;
  tenant_id: string;
  policy_id: string;
  policy_version_id: string | null;
  agent_id: string;
  credential_id: string | null;
  operation: string;
  before_state: string | null;
  after_state: string | null;
  occurred_at: string;
  correlation_id: string | null;
  request_id: string | null;
};

export const getPolicyAudit = (policyId: string, tenantId: string) =>
  request<AuditRecord[]>(`/policies/${policyId}/audit`, {}, true, tenantId);

export type ConflictReport = {
  conflict_type: string;
  target_policy_id: string;
  target_policy_version_id: string;
  conflicting_policy_id: string;
  conflicting_policy_version_id: string;
  relationship: string;
  target_effect: string;
  conflicting_effect: string;
  target_priority: number;
  conflicting_priority: number;
  explanation_code: string;
};

export const analyzeConflicts = (policyId: string, versionId: string, tenantId: string) =>
  request<ConflictReport[]>(
    `/policies/${policyId}/versions/${versionId}/analyze`,
    { method: 'POST', body: JSON.stringify({}) },
    false,
    tenantId
  );
