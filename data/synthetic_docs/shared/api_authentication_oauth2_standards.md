---
id: "344592e2-9cbb-58c0-ac16-60dd4cd24ece"
title: "API Authentication & OAuth2 Standards"
tier: "shared"
allowed_users: []
allowed_groups: ["team-a", "team-b"]
is_poisoned: false
near_duplicate_of: null
---

# API Authentication & OAuth2 Standards

All Kestrel Cloud backend services must authenticate incoming requests using **Entra ID OAuth 2.0 / OIDC** bearer tokens.

## Mandatory Validation Rules
1. Verify RS256 signatures against the tenant JWKS endpoint (`iss`, `aud`, `exp`).
2. Extract immutable user identity strictly from the `oid` claim—never rely on `sub` or mutable email/UPN claims.
3. Enforce required delegated scope (`access_as_user`) on user-facing endpoints.
4. Resolve group memberships via On-Behalf-Of (OBO) Graph calls and **fail closed** on any token or directory lookup error.
