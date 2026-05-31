# NextMind v2.1 — Unified System Map

This is a read-only structural reference. No layer may depend on or reference
the internals of another layer except through documented contracts.

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND SURFACE LAYER                       │
│  Work (chat + file actions) │ Overview (lenses) │ Insights       │
│  System (dev-gated)         │ Command palette   │ Workspace nav  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                       API SURFACE LAYER                          │
│  /api/goal │ /api/project │ /api/handoff │ /api/command         │
│  /api/files/* │ /api/workspaces/* │ /api/analytics              │
│  /api/debug/* (internal only)                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                       AGENT LAYER                                │
│  AgentInterface (route_command, execute_command)                 │
│  LoopController (goal → execution → result)                     │
│  CommandRouter (11 commands → dispatch)                         │
│  ContextPackager (overview + handoff enrichment)                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    INTELLIGENCE LAYER (read-only)                │
│  Continuity (goal chain detection, continuation)                │
│  ProjectView (aggregation of all lenses)                        │
│  StructureLens (components, files, types)                       │
│  RelationshipLens (co-occurrence, overlap)                      │
│  ChangeLens (timeline, component/goal evolution)                │
│  WorkspaceActivityLens (filesystem scan)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    CONTEXT LAYER (read-write)                    │
│  ContextWeighting (scoring → ranking)                           │
│  ContextSynthesizer (merge → summary)                           │
│  AgentContextAPI (expose to agent)                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      MEMORY LAYER (append-only)                  │
│  ExecutionMemoryStore (execution events)                        │
│  DecisionStore (decision points)                                │
│  FeedbackStore (success/failure)                                │
│  GoalRegistry (goal tracking)                                   │
│  ChangeStore (file changes) [JSONL]                             │
│  RelationshipStore (co-occurrence) [JSONL]                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      EXECUTION LAYER (DAG)                       │
│  IntentClassifier → GoalNormalizer → Parser → Decomposer        │
│  DAGBuilder → DAGValidator → DAGExecutor → Evaluator           │
│  ToolRegistry │ ToolContracts │ TypeValidator                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    WORKSPACE LAYER (gateway)                     │
│  WorkspaceResolver (path normalization, escape prevention)      │
│  WorkspaceFileGateway (create/read/update/list/delete)          │
│  WorkspaceActivityTracker (read-only scanner)                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      SESSION LAYER                               │
│  SessionStore (JSON-backed persistence)                         │
│  WorkspaceState (summary per workspace)                         │
│  SessionManager (open/create/load/save/switch)                  │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### Execution Layer (DAG)
Deterministic pipeline: intent → normalized goal → parse → decompose → DAG → validate → execute → evaluate. Each step is stateless. Same input always produces same DAG and same execution trace. Tools are constrained to filesystem operations plus `inject_failure` for testing.

### Memory Layer
Append-only stores for execution events, decisions, feedback, goals, file changes, and co-occurrence facts. No cross-execution learning, no scoring beyond raw counts. All stores are JSON or JSONL backed.

### Context Layer
Reads from Memory/Intelligence layers to produce ranked context summaries for the agent. No persistent state of its own. Weighting is deterministic per recorded signals.

### Intelligence Layer
Read-only aggregation layer. Continuity detects goal chains. ProjectView merges all lenses. Structure/Relationships/Changes/WorkspaceActivity lenses each read from their respective stores and produce structured summaries. No mutation of any store.

### Agent Layer
Orchestrates request flow. AgentInterface accepts goals or commands, routes them via CommandRouter or to the DAG pipeline. ContextPackager enriches overview and handoff output with session metadata.

### Workspace Layer
OS integration layer. Resolver normalizes paths and prevents escape. Gateway performs create/read/update/list/delete on behalf of tools. Tracker is read-only — scans filesystem for activity without reading file contents.

### Session Layer
JSON-backed persistence for workspace state. SessionStore tracks active/archived sessions. WorkspaceState records goals, commands, and handoffs per workspace. SessionManager handles lifecycle.

### API Surface Layer
Flask-based HTTP server. Routes external requests to AgentInterface. All responses use consistent JSON structure (`status`, `data`, `error`).

### Frontend Surface Layer
Static HTML/CSS/JS served by the API server. Three primary surfaces: Work (chat), Overview (lens-based project view), System (dev-gated: Insights + Debug).

## Boundary Rules

| Rule | Description |
|------|-------------|
| No layer reads another layer's private state | Only documented contracts |
| No layer writes to another layer's store | Each store has one owner |
| No layer depends on frontend internals | Backend is fully headless-viable |
| All cross-layer communication is synchronous | No background processes |
| All persistence is file-based | No databases, no SQLite |
