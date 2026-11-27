---
id: "5c0f3b4a-91e4-5bcd-ac8d-301602f4dba0"
title: "Relevance Evaluation Benchmark Report"
tier: "team-b"
allowed_users: []
allowed_groups: ["team-b"]
is_poisoned: false
near_duplicate_of: null
---

# Relevance Evaluation Benchmark Report

**Benchmark Suite:** Kestrel-Eval-v3 (1,200 annotated queries across 8 domains)

## Results Summary
| Configuration | Recall@10 | NDCG@10 | p95 Latency |
| :--- | :---: | :---: | :---: |
| BM25 Only | 0.71 | 0.64 | 18 ms |
| Dense Vector Only | 0.83 | 0.76 | 34 ms |
| Hybrid (RRF + Cross-Encoder) | **0.92** | **0.87** | 68 ms |

## Key Takeaway
Reciprocal Rank Fusion (RRF, `k=60`) followed by a lightweight cross-encoder reranker on top-25 candidates yields the best accuracy-to-latency tradeoff.
