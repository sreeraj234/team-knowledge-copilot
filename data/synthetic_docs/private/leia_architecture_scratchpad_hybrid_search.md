---
id: "d2ab330e-ec17-5e7c-baff-1b7036f94b79"
title: "Leia Architecture Scratchpad: Hybrid Search"
tier: "private-leia"
allowed_users: ["leia"]
allowed_groups: []
is_poisoned: false
near_duplicate_of: null
---

# Leia Architecture Scratchpad: Hybrid Search

**Personal Scratchpad — Leia**

## Experiment Notes: Pre-Filtered HNSW vs. Iterative Scan
- With selective ACL filters (e.g., `allowed_group_ids && ARRAY[...]`), standard HNSW `ef_search=40` can under-fetch if `< 5%` of corpus matches the user's groups.
- Need to benchmark pgvector 0.8 iterative index scans (`SET hnsw.iterative_scan = strict_order;`) vs. exact scan fallback when candidate count `< 100`.
- Remember: **never** post-filter after `LIMIT 8`, or unauthorized chunks could silently crowd out authorized ones!
