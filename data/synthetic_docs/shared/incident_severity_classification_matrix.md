---
id: "2e45630c-5b69-54eb-a49a-cc1a9b5c56b0"
title: "Incident Severity Classification Matrix"
tier: "shared"
allowed_users: []
allowed_groups: ["team-a", "team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Incident Severity Classification Matrix

Consistent severity classification ensures rapid escalation across all Kestrel Cloud teams.

## Levels
- **SEV-1 (Critical):** Complete outage of core APIs, data loss, security breach, or unauthorized cross-tenant/cross-group data exposure. Page immediately; postmortem required within 48 hours.
- **SEV-2 (High):** Significant degradation (`> 5%` error rate or `> 2x` latency SLA) with no workaround. Page primary on-call.
- **SEV-3 (Medium):** Minor feature impairment or single non-critical job failure. Handle during business hours.
- **SEV-4 (Low):** Cosmetic issues or minor documentation gaps. Track in backlog.
