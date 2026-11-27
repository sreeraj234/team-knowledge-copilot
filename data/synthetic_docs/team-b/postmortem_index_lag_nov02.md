---
id: "185da26e-bbce-5609-8b7a-f2cca2567cec"
title: "Postmortem: Index Lag Incident Nov 02"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Postmortem: Index Lag Incident Nov 02

**Date:** November 02 | **Severity:** SEV-2 | **Duration:** 47 minutes | **Author:** Team-B

## Summary
Newly uploaded documents took up to 45 minutes to appear in search results due to consumer lag on `search.ingest.v1`.

## Root Cause
A single tenant uploaded a 120,000-page archive in one burst, saturating all 8 `embed-worker` partitions because partitioning was keyed by `document_id` without per-tenant rate limiting.

## Action Items
1. Implement token-bucket per-tenant ingestion quotas (`SRCH-289`, completed).
2. Separate bulk-backfill queue from real-time interactive upload queue (`SRCH-294`, in progress).
