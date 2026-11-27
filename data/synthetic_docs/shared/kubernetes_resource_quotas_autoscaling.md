---
id: "ff3255fd-4d35-5972-986d-828c466a833e"
title: "Kubernetes Resource Quotas & Autoscaling"
tier: "shared"
allowed_users: []
allowed_groups: ["team-a", "team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Kubernetes Resource Quotas & Autoscaling

Standardized resource requests and HorizontalPodAutoscaler (HPA) settings prevent noisy-neighbor CPU throttling.

## Baseline Defaults
- Always set `requests.cpu == limits.cpu`? No—set `requests.cpu` to P50 usage and omit `limits.cpu` for latency-sensitive APIs, while setting `requests.memory == limits.memory` to prevent unexpected OOM kills.
- Configure HPA target CPU utilization at `65%` with `minReplicas: 2` across at least 2 availability zones.
- Include a `PodDisruptionBudget` (`minAvailable: 1`) on all stateless deployments.
