---
id: "5d2f9c69-1667-5daa-8c5b-10c4aa5f789a"
title: "Payment Gateway Failover Design"
tier: "team-a"
allowed_users: []
allowed_groups: ["team-a"]
is_poisoned: false
near_duplicate_of: null
---

# Payment Gateway Failover Design

To maintain `99.99%` checkout availability, Team-A routes card authorizations across two independent payment processors: **PrimaryPay** (`85%` weight) and **BackupPay** (`15%` warm traffic).

## Circuit Breaker Rules
- Trip to `100%` BackupPay if PrimaryPay 5xx rate exceeds `3%` over a 2-minute sliding window or `p95` latency exceeds `2,500 ms`.
- Half-open probe sends `1%` synthetic health-check authorizations every 60 seconds before restoring primary traffic.

## Token Portability
Card tokens are stored in our PCI-scoped vault (`kestrel-vault`) so failover requires zero customer re-entry.
