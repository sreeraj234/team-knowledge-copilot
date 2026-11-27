---
id: "d3544f3d-d735-56af-8393-d8624f26ec56"
title: "Luke Draft RFC: Async Ledger Compaction"
tier: "private-luke"
allowed_users: ["luke"]
allowed_groups: []
is_poisoned: false
near_duplicate_of: null
---

# Luke Draft RFC: Async Ledger Compaction

**Status:** Personal Draft (Not Yet Shared) | **Author:** Luke

## Problem
`ledger_entries` grows by ~18M rows per month. Historical closed-period rows (> 2 years old) slow down vacuuming and backup windows.

## Idea
Introduce an immutable monthly checkpoint snapshot (`ledger_checkpoints`) signed with SHA-256 Merkle hashes, then archive raw entries older than 24 months to Parquet on cold S3 storage.

## Open Questions
- Need Finance sign-off on audit-trail query SLA (is `< 30s` via Athena acceptable for 2+ year old audits?).
