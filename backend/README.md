# NextMind — Deterministic DAG Execution Engine

> **ARCHITECTURAL BOUNDARY**: This system is a deterministic execution engine. It does not model project intelligence, reasoning, autonomy, or planning beyond DAG construction. It converts structured intent into a directed acyclic graph and executes it step-by-step over a constrained tool set. No governance, coherence, simulation, or cognitive state systems exist or will be added.

## Pipeline

```
Intent → IntentClassifier → GoalNormalizer → SimpleParser/Decomposer → DAGBuilder → DAGValidator → DAGExecutor → Evaluator
```

## Data Contract

| Direction | Type | Description |
|-----------|------|-------------|
| Input | `goal: str` | Natural language or structured intent description |
| Output | `ExecutionResult` | Execution status, per-node trace, step count |

## Design Rules

1. **No intelligence layer** — the system has no reasoning, planning, or autonomy
2. **No governance** — no authority hierarchy, no constitution, no policy enforcement
3. **No simulation** — no dry-run, no simulated execution, no projection
4. **No memory** — no cross-execution state, no learning, no experience accumulation
5. **No recovery system** — no rollback engine, no transaction journal, no recovery store
6. **No frontend** — CLI only, no HTTP API, no React UI
7. **Minimal tools** — filesystem operations only (write, read, list_dir) plus inject_failure
8. **Deterministic by construction** — same input always produces same output
