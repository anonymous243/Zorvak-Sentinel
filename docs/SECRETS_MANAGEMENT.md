# ZORVAK SENTINEL — Production Secrets Management Guide

## 1. Principles
- **Zero Plaintext Secrets**: No credentials, API tokens, Ed25519 private keys, or JWT secrets may ever be committed to Git.
- **Provider-Neutral Interface**: In production, application processes read secrets from environment variables, which must be injected at container startup by a dedicated Secret Manager (e.g., AWS Secrets Manager, HashiCorp Vault, Doppler, or Kubernetes Secrets).

## 2. Key Secrets Inventory
| Secret Name | Minimum Entropy | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string with SSL | Primary database connection |
| `JWT_SECRET` | >= 32 characters (256-bit cryptographically random) | Human control plane session JWT signature |
| `AGENT_SIGNING_KEYS` | Ed25519 private keys (stored exclusively on client agents) | Action request signing |

## 3. Production Deployment Guidelines
- **AWS Secrets Manager / ECS**:
  Inject secrets directly into task definition:
  ```json
  "secrets": [
    { "name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:...:sentinel/db" },
    { "name": "JWT_SECRET", "valueFrom": "arn:aws:secretsmanager:...:sentinel/jwt" }
  ]
  ```
- **Kubernetes / HashiCorp Vault**:
  Use the Vault Agent Injector to mount secrets as environment variables into the pod spec without persisting to disk.
