---
id: "c8577f18-5d4b-514e-83c5-bd71bf238853"
title: "Cold-Start Ranking Fallback Design"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Cold-Start Ranking Fallback Design

New tenants with fewer than 50 indexed documents lack historical click signals for learned-to-rank models.

## Fallback Strategy
- Bypass the GBDT personalization layer when `tenant_doc_count < 50`.
- Rank purely by normalized Hybrid RRF score (`0.7 * dense_cosine + 0.3 * bm25`) plus recency boost (`half_life = 30 days`).
- Gradually blend behavioral features once a tenant crosses 500 recorded search impressions.
