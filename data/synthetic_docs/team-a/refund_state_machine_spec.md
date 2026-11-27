---
id: "9900f852-e2c4-5bf9-93ee-fd35a5ba7158"
title: "Refund State Machine Specification"
tier: "team-a"
allowed_users: []
allowed_groups: ["team-a"]
is_poisoned: false
near_duplicate_of: null
---

# Refund State Machine Specification

Refunds in `ledger-api` follow a strict deterministic finite state machine.

## States & Transitions
- `REQUESTED` -> `PENDING_GATEWAY` (once balance check passes)
- `PENDING_GATEWAY` -> `SUCCEEDED` | `FAILED`
- `FAILED` -> `MANUAL_REVIEW` (after 3 exponential backoff retries)

## Invariants
- Total refunded amount across all `SUCCEEDED` and `PENDING_GATEWAY` refunds for a charge must never exceed `original_charge_amount_cents`.
- Partial refunds emit a proportional credit memo entry in `ledger_entries`.
