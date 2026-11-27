---
id: "4d02d767-a395-5c4a-8345-436cf78c5414"
title: "Database Migration Checklist"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: "database-migration-checklist"
---

# Database Migration Checklist

**Scope:** `pgvector` HNSW indexes and `feature_store_db` (Team-B)

## Pre-Migration Gates
- [ ] Rebuilding HNSW indexes on `document_chunks` (`vector(768)`) must run off-peak with `maintenance_work_mem = '4GB'`.
- [ ] Validate cosine similarity recall@10 on the golden eval set before swapping index aliases.
- [ ] Ensure `embed-worker` consumers are paused during embedding dimension changes.
- [ ] Verify feature store Redis snapshot is fresh (`< 15 minutes` old).

## Rollback Plan
Keep the previous `hnsw_v1` index online until `hnsw_v2` passes 24 hours of shadow traffic parity checks.
