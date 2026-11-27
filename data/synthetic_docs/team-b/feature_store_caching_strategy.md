---
id: "dfd04240-fa1f-5c5c-a063-a2b4d57ec1ac"
title: "Feature Store Caching Strategy"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Feature Store Caching Strategy

`ranker-service` fetches document freshness, click-through priors, and popularity signals from Redis Cluster.

## Caching Rules
- **TTL:** Popularity counters use a 15-minute TTL with probabilistic early expiration to prevent thundering herds.
- **Compression:** Feature vectors are serialized as MessagePack + LZ4, reducing Redis memory footprint by `58%`.
- **Fallback:** On Redis timeout (`> 5 ms`), the ranker falls back to static default priors (`0.5`) so search availability is never blocked.
