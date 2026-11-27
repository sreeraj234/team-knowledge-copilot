---
id: "a188be84-1050-5cc9-a2bb-63bf88a24d0a"
title: "Observability: Logging & Tracing Standards"
tier: "shared"
allowed_users: []
allowed_groups: ["team-a", "team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Observability: Logging & Tracing Standards

All services emit structured JSON logs and OpenTelemetry traces to our central collector.

## Logging Rules
- Include `trace_id`, `span_id`, `service`, `env`, and `tenant_id` on every log line.
- **Never** log bearer tokens, API keys, PII, or raw document contents at `INFO` or `DEBUG` in production.
- Use `WARNING` for recoverable downstream retries and `ERROR` only for actionable failures.

## Tracing
Propagate W3C `traceparent` headers across all HTTP and Kafka boundaries.
