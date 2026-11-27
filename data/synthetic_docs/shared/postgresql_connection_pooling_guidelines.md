---
id: "1bd964d5-07bc-5f38-afc8-8a6d25bc0585"
title: "PostgreSQL Connection Pooling Guidelines"
tier: "shared"
allowed_users: []
allowed_groups: ["team-a", "team-b"]
is_poisoned: false
near_duplicate_of: null
---

# PostgreSQL Connection Pooling Guidelines

All production Python services connect to PostgreSQL through **PgBouncer** in `transaction` pooling mode.

## Configuration Standards
- Set SQLAlchemy/psycopg client pool `max_size = 10` per pod to avoid exhausting PgBouncer slots.
- Always configure `statement_timeout = 5000` (5 seconds) on interactive API connections.
- Avoid session-level prepared statements or temporary tables when using transaction pooling.
- Monitor `pgbouncer_pools_cl_waiting` in Grafana; alert if waiting clients `> 20` for 3 minutes.
