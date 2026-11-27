---
id: "19446808-bfa8-54ec-ad35-af9e74d90963"
title: "CI/CD Pipeline & Release Gates"
tier: "shared"
allowed_users: []
allowed_groups: ["team-a", "team-b"]
is_poisoned: false
near_duplicate_of: null
---

# CI/CD Pipeline & Release Gates

Every pull request targeting `main` must pass all automated GitHub Actions gates before merge.

## Required Checks
- **Secret Scanning:** TruffleHog verified-secret scan across commit history.
- **Lint & Format:** `ruff check` and `ruff format --check` with zero warnings.
- **Unit & Integration Tests:** `pytest` suite running against ephemeral `pgvector` and Redis containers.
- **Code Review:** At least 1 approving review from a CODEOWNER in the modified service directory.
