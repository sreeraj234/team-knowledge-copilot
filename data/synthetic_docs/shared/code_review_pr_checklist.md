---
id: "baf13cb1-e6a4-5d8f-aea3-21ba0d8ac125"
title: "Code Review & PR Checklist"
tier: "shared"
allowed_users: []
allowed_groups: ["team-a", "team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Code Review & PR Checklist

Good code reviews keep Kestrel Cloud secure, maintainable, and easy to operate.

## Reviewer Checklist
- **Security:** Are authorization checks enforced server-side before data access? Are inputs validated?
- **Scope:** Is the PR focused on a single logical change (`< 400` lines preferred)?
- **Tests:** Do tests cover both happy paths and negative/failure cases (e.g., unauthorized access)?
- **Operability:** Are new config flags documented in `.env.example` with safe defaults?
