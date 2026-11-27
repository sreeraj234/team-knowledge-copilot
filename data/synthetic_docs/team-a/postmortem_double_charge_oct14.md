---
id: "019040e9-1b4d-5cb2-a460-f4de739c9cb5"
title: "Postmortem: Double-Charge Incident Oct 14"
tier: "team-a"
allowed_users: []
allowed_groups: ["team-a"]
is_poisoned: false
near_duplicate_of: null
---

# Postmortem: Double-Charge Incident Oct 14

**Date:** October 14 | **Severity:** SEV-1 | **Duration:** 23 minutes | **Author:** Team-A

## Summary
A retry storm in `billing-worker` caused 142 tenants to be charged twice for monthly seat overages.

## Root Cause
During a Redis failover, the idempotency key cache returned transient connection timeouts. The worker treated cache lookup errors as "key not seen" (fail-open) instead of aborting the charge attempt.

## Action Items
1. Change idempotency lookup to **fail-closed** on Redis errors (`PAY-412`, completed).
2. Add a unique partial index on `(tenant_id, billing_period, charge_type)` in `billing_db` (`PAY-415`, completed).
3. Automated refunds issued to all 142 affected accounts within 2 hours.
