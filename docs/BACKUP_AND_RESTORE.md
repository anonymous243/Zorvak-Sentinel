# ZORVAK SENTINEL — Disaster Recovery, Backup & Restore Strategy

## 1. Objectives & Metrics
- **Recovery Point Objective (RPO)**: < 5 minutes (Continuous Write-Ahead Logging / WAL archiving).
- **Recovery Time Objective (RTO)**: < 30 minutes (Automated point-in-time recovery).

## 2. PostgreSQL Backup Architecture (Production)
- **Primary Mechanism**: Continuous physical base backups + WAL archiving using tools like `pgBackRest` or AWS RDS/Aurora automated snapshotting (for cloud-managed PostgreSQL like Neon).
- **Encryption**: AES-256 for all backup archives at rest; TLS 1.3 in transit.
- **Retention Schedule**:
  - Hourly differential backups (retained 7 days).
  - Daily full base backups (retained 30 days).
  - Monthly archive snapshots (retained 1 year for compliance audit).

## 3. Restore Verification Procedure
1. **Isolated Sandbox Provisioning**:
   - Provision a staging PostgreSQL instance matching the target PostgreSQL version (PostgreSQL 18.x).
2. **Base Backup Restoration**:
   ```bash
   pgbackrest --stanza=sentinel --delta restore
   ```
3. **Point-In-Time Recovery (PITR)**:
   - Configure `recovery_target_time = '2026-10-11 20:00:00 UTC'` to roll forward WAL to the exact pre-incident timestamp.
4. **Data Integrity & Consistency Verification**:
   - Verify table row counts against daily metric snapshots:
     ```sql
     SELECT COUNT(*) FROM security_events;
     SELECT COUNT(*) FROM evidence_ledger_records;
     ```
   - Verify cryptographic chain integrity in `evidence_ledger_records`:
     - Recalculate SHA-256 hashes sequentially from `seq_num = 1` up to the latest record.
5. **Alembic Schema Verification**:
   ```bash
   alembic check
   ```
