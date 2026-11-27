---
id: "4099107b-8829-5254-8e6b-b7fb7884d2cb"
title: "Ledger Service Architecture"
tier: "team-a"
allowed_users: []
allowed_groups: ["team-a"]
is_poisoned: false
near_duplicate_of: null
---

# Ledger Service Architecture

The Kestrel Cloud **Ledger Service** implements an immutable, append-only double-entry accounting store backed by PostgreSQL.

## Core Concepts
- **Accounts:** Typed as `ASSET`, `LIABILITY`, `REVENUE`, or `EXPENSE`, scoped per tenant.
- **Journal Entries:** Every financial state transition creates a balanced pair of debit and credit `ledger_entries` sharing a `journal_id`.
- **Idempotency:** Callers must supply an `Idempotency-Key` header (UUIDv4). Keys are cached in Redis for 24 hours and persisted in `journal_idempotency_keys`.

## Consistency Guarantees
All balance checks run under `SERIALIZABLE` isolation for payout approvals, while read-only statement exports query the async read replica.
