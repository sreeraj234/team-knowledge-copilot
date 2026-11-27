---
id: "a938d2b8-5533-5c2a-9cbc-482f57034579"
title: "Team-B Q4 Roadmap & OKRs"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Team-B Q4 Roadmap & OKRs

**Team:** Team-B (Search & Recommendations) | **Quarter:** Q4

## Objectives & Key Results
1. **Hybrid Retrieval Rollout:** Ship RRF + cross-encoder reranking to `100%` of production tenants (`NDCG@10 >= 0.85`).
2. **Sub-100ms Search p95:** Reduce end-to-end query latency from `135 ms` to `< 90 ms` via quantized `int8` vector pre-filtering.
3. **Ingestion Isolation:** Eliminate noisy-neighbor index lag via dedicated bulk-import queues.
