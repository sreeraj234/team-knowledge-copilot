---
id: "5c5271ef-aa21-5400-8daa-80163845156a"
title: "Q4 Service Deployment Runbook"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: "q4-service-deployment-runbook"
---

# Q4 Service Deployment Runbook

**Applies To:** `search-router`, `embed-worker`, and `ranker-service` (Team-B)

## Canary Rollout Procedure
1. Deploy canary revision (`10%` shadow + `5%` live traffic) in `us-west-prod` with `RANKER_LOG_FEATURES=true`.
2. Compare `ndcg_at_10` and `search_p95_ms` against baseline for 30 minutes.
3. Verify GPU inference memory stays under `75%` on `ranker-service` nodes.
4. Promote to `100%` and update model registry tag `search-q4-YYYY.MM.DD`.

## Emergency Abort
Run `kubectl rollout undo deployment/ranker-service -n search-prod` and post in `#team-b-releases`.
