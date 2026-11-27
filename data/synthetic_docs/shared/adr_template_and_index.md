---
id: "59320af1-3d32-5073-ac3e-8bf75cde17d3"
title: "Architecture Decision Record (ADR) Template & Index"
tier: "shared"
allowed_users: []
allowed_groups: ["team-a", "team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Architecture Decision Record (ADR) Template & Index

Significant architectural choices must be documented as lightweight ADRs in `docs/adr/`.

## ADR Template
- **Status:** Proposed | Accepted | Superseded
- **Context:** What problem and constraints are we solving?
- **Decision:** What option did we choose and why?
- **Consequences:** Trade-offs, operational impact, and migration path.

## Active Index
- `ADR-001`: Use PostgreSQL + `pgvector` with pre-retrieval SQL ACL filtering
- `ADR-002`: Adopt Entra ID OBO flow for downstream Graph group resolution
