---
id: "1dc95294-1b9f-526c-9535-9be31804d0f8"
title: "On-Call Escalation Policy"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: "on-call-escalation-policy"
---

# On-Call Escalation Policy

**Owner:** Team-B (Search & Recommendations Engineering)
**Rotation Cadence:** Weekly handoff every Thursday at 16:00 UTC

## Alerting Tiers
1. **SEV-1 (Search API 5xx > 1% or Indexer Stalled > 15m):** Primary on-call must acknowledge within 5 minutes via PagerDuty schedule `KESTREL-SEARCH-PRIMARY`. Escalate to `KESTREL-SEARCH-ML` after 10 minutes.
2. **SEV-2 (Embedding Queue Lag > 20,000 docs):** Acknowledge within 15 minutes. Scale `embed-worker` HPA replicas or switch to fast-fallback lexical mode.

## Runbook Shortcuts
- Enable BM25-only fallback: `kestrel-cli search set-mode --lexical-only`
- Check shard health: `curl -s http://search-router.internal:9200/_cluster/health | jq .`
