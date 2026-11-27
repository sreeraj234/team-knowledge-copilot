---
id: "fd4de531-a1f0-504f-8109-532fec428b99"
title: "Database Migration Checklist"
tier: "team-a"
allowed_users: []
allowed_groups: ["team-a"]
is_poisoned: false
near_duplicate_of: "database-migration-checklist"
---

# Database Migration Checklist

**Scope:** PostgreSQL `billing_db` and `ledger_db` clusters (Team-A)

## Pre-Migration Gates
- [ ] All schema changes on `ledger_entries` (450M+ rows) must use `CREATE INDEX CONCURRENTLY` and `SET lock_timeout = '2s'`.
- [ ] Verify double-entry invariant constraints remain intact in staging replay tests.
- [ ] Confirm zero long-running reconciliation transactions (`> 60s`) are active before applying DDL.
- [ ] Snapshot `billing_db` read replica before executing destructive column drops.

## Rollback Plan
Maintain dual-write triggers for at least 48 hours on any column rename affecting `invoices` or `payment_intents`.
