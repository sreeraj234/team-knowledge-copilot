---
id: "861a37da-5b72-5da0-8b1d-9158a035612a"
title: "Q4 Service Deployment Runbook"
tier: "team-a"
allowed_users: []
allowed_groups: ["team-a"]
is_poisoned: false
near_duplicate_of: "q4-service-deployment-runbook"
---

# Q4 Service Deployment Runbook

**Applies To:** `ledger-api`, `invoice-renderer`, and `payout-scheduler` (Team-A)

## Canary Rollout Procedure
1. Deploy canary pod (`5%` traffic weight) to `us-east-prod` with `LEDGER_SHADOW_VERIFY=true`.
2. Monitor `payment_intent_error_rate` and `ledger_commit_p99_ms` for 20 minutes.
3. Promote to `50%` only if idempotency conflict rate stays below `0.02%`.
4. Complete `100%` rollout and tag release `pay-q4-YYYY.MM.DD`.

## Emergency Abort
Run `helm rollback ledger-api --namespace payments-prod` and notify `#team-a-deployments`.
