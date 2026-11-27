---
id: "b1fbcdfe-8a1d-50a9-9a84-7b9907319a7c"
title: "Service-Level Objectives (SLO) Framework"
tier: "shared"
allowed_users: []
allowed_groups: ["team-a", "team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Service-Level Objectives (SLO) Framework

Every Tier-1 service defines explicit Availability and Latency SLOs tracked over a 28-day rolling window.

## Standard Targets
- **Availability:** `99.95%` successful non-5xx responses (`21.6 minutes` monthly error budget).
- **Latency:** `p95 < 250 ms` for synchronous REST endpoints; `p99 < 1,000 ms` for RAG retrieval queries.

## Error Budget Policy
When a service burns `> 50%` of its monthly error budget in 7 days, feature launches pause in favor of reliability hardening.
