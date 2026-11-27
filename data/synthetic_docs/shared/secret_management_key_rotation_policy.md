---
id: "f85bafd5-822d-5223-974a-50ac20899b0e"
title: "Secret Management & Key Rotation Policy"
tier: "shared"
allowed_users: []
allowed_groups: ["team-a", "team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Secret Management & Key Rotation Policy

Secrets must never be committed to Git or stored in plaintext environment files in shared environments.

## Policy Requirements
- Production secrets live in **Azure Key Vault / HashiCorp Vault** and are injected via CSI driver at pod startup.
- Client secrets (`API_CLIENT_SECRET`), webhook HMAC keys, and database passwords rotate every **90 days**.
- If a secret is accidentally pushed to any branch, revoke it immediately, purge history if needed, and file a `SEV-1` security incident.
