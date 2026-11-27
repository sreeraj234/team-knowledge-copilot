---
id: "bfa6c787-7639-5d41-b1f7-2216285fdeda"
title: "Billing Cycle Reconciliation Job"
tier: "team-a"
allowed_users: []
allowed_groups: ["team-a"]
is_poisoned: false
near_duplicate_of: null
---

# Billing Cycle Reconciliation Job

The nightly **Billing Reconciliation Job** runs at 02:00 UTC to verify that internal `invoices` match settled transactions from external settlement reports.

## Job Stages
- **Extract:** Pull previous day's CSV settlement files from S3 bucket `kestrel-settlements-prod`.
- **Match:** Join on `payment_intent_id` and compare `net_amount_cents`, `fee_cents`, and `currency`.
- **Discrepancy Triage:** Any delta `> $0.01` opens an automated Jira ticket in project `PAYOPS` and emits metric `reconciliation_mismatch_count`.

## SLA
Reconciliation must complete before 05:00 UTC so Finance can close daily revenue dashboards.
