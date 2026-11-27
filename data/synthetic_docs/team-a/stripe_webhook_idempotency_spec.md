---
id: "e49383fe-3edf-5eba-824c-cf50ede83aae"
title: "Gateway Webhook Idempotency Spec"
tier: "team-a"
allowed_users: []
allowed_groups: ["team-a"]
is_poisoned: false
near_duplicate_of: null
---

# Gateway Webhook Idempotency Spec

External payment processors occasionally deliver duplicate or out-of-order webhook events. Team-A's ingestion gateway enforces strict deduplication.

## Processing Pipeline
1. Verify HMAC-SHA256 signature header (`X-Gateway-Signature`) against the rotated secret in Vault.
2. Insert `(provider, event_id)` into `processed_webhook_events` with `ON CONFLICT DO NOTHING`.
3. If inserted, enqueue the normalized payload onto Kafka topic `payments.webhooks.v2`; otherwise return `200 OK` immediately.

## Out-of-Order Handling
State transitions use monotonic sequence numbers (`event_created_at` + `state_version`) so stale `charge.pending` events never overwrite `charge.settled`.
