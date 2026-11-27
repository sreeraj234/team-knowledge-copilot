---
id: "a3e712d4-7970-5bb1-ba18-d54d4408b2ea"
title: "Search Indexer Sharding Architecture"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Search Indexer Sharding Architecture

Kestrel Cloud's **Search Indexer** partitions tenant corpora across 16 logical shards using consistent hashing on `tenant_id`.

## Design Highlights
- **Routing:** `search-router` computes `murmur3(tenant_id) % 16` to target only the relevant shard, avoiding scatter-gather fanout for single-tenant queries.
- **Hot-Tenant Isolation:** Enterprise tenants exceeding `5M` chunks are promoted to dedicated isolated shards via dynamic routing table entries in etcd.
- **Compaction:** Background merge workers compact tombstone segments nightly at 03:00 UTC.
