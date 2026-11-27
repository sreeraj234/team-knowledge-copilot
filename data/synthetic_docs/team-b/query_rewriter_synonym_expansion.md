---
id: "be492e4c-3b0d-5d53-b662-c7139605b86d"
title: "Query Rewriter & Synonym Expansion"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Query Rewriter & Synonym Expansion

`query-rewriter` normalizes user queries before vector and BM25 retrieval.

## Pipeline Steps
- **Spell Correction:** SymSpell dictionary built from domain-neutral technical terms (max edit distance 2).
- **Acronym Expansion:** Expands common engineering acronyms (e.g., `k8s -> kubernetes`, `pg -> postgres`) into weighted OR clauses for BM25.
- **Latency Budget:** Total rewrite step must complete in `< 8 ms` p99; if exceeded, pass raw query straight to retrieval.
