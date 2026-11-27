---
id: "63672e86-0e00-58e9-a322-7272e9439a04"
title: "On-Call Escalation Policy"
tier: "team-a"
allowed_users: []
allowed_groups: ["team-a"]
is_poisoned: false
near_duplicate_of: "on-call-escalation-policy"
---

# On-Call Escalation Policy

**Owner:** Team-A (Payments & Ledger Engineering)
**Rotation Cadence:** Weekly handoff every Tuesday at 09:00 UTC

## Alerting Tiers
1. **SEV-1 (Ledger Drift or Payment Outage):** Primary on-call engineer must acknowledge within 5 minutes via PagerDuty schedule `KESTREL-PAY-PRIMARY`. If unacknowledged after 10 minutes, escalate to `KESTREL-PAY-SECONDARY` and the Payments Engineering Manager.
2. **SEV-2 (Webhook Backlog > 5,000 events):** Acknowledge within 15 minutes. Check dead-letter queue depth on `pay-webhook-worker` and verify downstream gateway latency.

## Runbook Shortcuts
- Freeze automated payouts: `kestrel-cli billing payouts --pause --reason="sev1-investigation"`
- Inspect ledger balance checksums: `SELECT currency, SUM(amount_cents) FROM ledger_entries GROUP BY currency;`
