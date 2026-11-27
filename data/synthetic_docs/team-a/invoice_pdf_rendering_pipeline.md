---
id: "706a61ac-75d6-5186-87a7-ee4dbefa5d78"
title: "Invoice PDF Rendering Pipeline"
tier: "team-a"
allowed_users: []
allowed_groups: ["team-a"]
is_poisoned: false
near_duplicate_of: null
---

# Invoice PDF Rendering Pipeline

`invoice-renderer` generates localized PDF invoices for enterprise tenants using a sandboxed Chromium headless pool.

## Architecture
- **Trigger:** Consumes `invoice.finalized` events from `payments.invoices.v1`.
- **Templating:** Renders HTML from versioned Jinja2 templates with tax line items and tenant VAT IDs.
- **Storage:** Uploads immutable PDFs to `s3://kestrel-invoices-archive/{tenant_id}/{year}/{invoice_id}.pdf` with Object Lock enabled.

## Performance Limits
Each worker pod caps concurrent renders at 4 tabs to keep memory below `1.5 GiB`.
