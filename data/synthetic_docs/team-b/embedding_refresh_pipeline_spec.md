---
id: "89af3566-88be-5f7b-b45a-2d716f11bf13"
title: "Embedding Refresh Pipeline Spec"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Embedding Refresh Pipeline Spec

When Team-B upgrades the sentence embedding model, `embed-worker` re-embeds historical chunks without causing search downtime.

## Blue/Green Vector Columns
1. Add nullable `embedding_v2 vector(768)` alongside active `embedding_v1`.
2. Backfill batches of 500 chunks via Ray workers throttled to `40%` GPU utilization.
3. Build HNSW index on `embedding_v2` (`m=16, ef_construction=128`).
4. Flip feature flag `SEARCH_ACTIVE_EMBEDDING_COL=embedding_v2` and drop `embedding_v1` after 7 days.
