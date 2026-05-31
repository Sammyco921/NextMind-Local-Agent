# NextMind v2.1 — Surface Contract

## 1. External Interaction Surfaces

### CLI Surface

Entry point: `backend/main.py`

| Operation | Description |
|-----------|-------------|
| Goal execution | Submit a natural-language or structured goal → get trace + result |
| Context inspection | View current session state, active goals, recent execution |
| File operations | Create, read, update, delete, list files through workspace gateway |
| Handoff export | Generate a handoff summary (standard mode only) |

**Excluded from CLI exposure:** DAG internals, memory store dumps, scoring weights,
continuity chains, relationship graphs, session raw data.

### API Surface

Base URL: `http://localhost:5001` (configurable)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/goal` | POST | Execute a goal, return trace + result |
| `/api/project?lens=` | GET | Read-only aggregation (overview, history, continuity, structure, changes, relationships, workspace) |
| `/api/handoff?mode=standard` | GET | Generate handoff package |
| `/api/command` | POST | Route a quick command string |
| `/api/files/create` | POST | Create a file |
| `/api/files/read` | POST | Read a file |
| `/api/files/list` | POST | List directory contents |
| `/api/workspaces` | GET | List all workspaces |
| `/api/workspaces/current` | GET | Get current workspace info |
| `/api/workspaces/switch` | POST | Switch active workspace |
| `/api/analytics` | GET | Session analytics (tasks, success rates, recurring failures) |
| `/api/debug/events` | GET | Execution debug events (internal) |
| `/api/debug/decisions` | GET | Decision log (internal) |
| `/api/debug/feedback` | GET | Feedback log (internal) |

**Official surface** (for external consumers): `/api/goal`, `/api/project`, `/api/handoff`,
`/api/command`, `/api/files/*`, `/api/workspaces/*`.

**Internal endpoints** (may change without notice): `/api/analytics`, `/api/debug/*`.

### Frontend Surface

| Surface | Tab | Contents | Default visibility |
|---------|-----|----------|-------------------|
| Work | Work | Chat, file actions, command palette | Always |
| Overview | Overview | Lens-based project view (default: Overview lens) | Always |
| Insights | Insights (dev-gated) | Goal stats, success/failure rates, recurring issues | Hidden, dev toggle |
| System | System (dev-gated) | Debug event/decision/feedback logs | Hidden, dev toggle |

**Terminology mapping** (frontend labels only, backend names unchanged):

| Old (backend/internal) | Frontend label |
|------------------------|----------------|
| Project View | Overview |
| Execution | Work |
| Goals | Tasks |
| Decisions | History |
| Feedback | Insights |
| Continuity | Continue Work |
| Relationships | Connections |
| Structure | Layout |

---

## 2. Input/Output Contracts

### InputContract (goal execution)

```json
{
  "goal": "string (required) — natural language or structured intent",
  "context_scope": "string (optional) — 'workspace' | 'session' | 'project'",
  "execution_mode": "string (optional) — 'normal' | 'strict'",
  "flags": ["string (optional) — additional execution flags"]
}
```

### OutputContract (goal execution response)

```json
{
  "status": "'success' | 'failed' | 'clarification_required'",
  "result": {
    "summary": "string — human-readable outcome",
    "output": "any — final output artifact (if any)"
  },
  "trace": {
    "steps": [
      {
        "label": "string — step description",
        "status": "'success' | 'failed' | 'running'",
        "tool": "string — tool used (if applicable)"
      }
    ],
    "summary": "string — overall execution summary",
    "status_line": "string — one-line status"
  },
  "continuation": {
    "is_continuation": "boolean",
    "parent_description": "string (if continuation)"
  },
  "meta": {
    "goal": "string — original goal",
    "status": "'success' | 'failed' | 'clarification_required'",
    "execution_time_ms": "number (approximate)"
  }
}
```

### ProjectContract (project view response)

```json
{
  "lens": "'overview' | 'history' | 'continuity' | 'structure' | 'changes' | 'relationships' | 'workspace'",
  "goal_count": { "total": "number", "active": "number", "blocked": "number", "completed": "number" },
  "...": "lens-specific fields (see source)",
  "workspace": {
    "name": "string",
    "last_opened": "string (ISO timestamp)"
  }
}
```

### CommandContract (command route response)

```json
{
  "command": "'execute_goal' | 'create_file' | 'read_file' | 'update_file' | 'delete_file' | 'create_folder' | 'list_workspace' | 'show_overview' | 'show_structure' | 'show_relationships' | 'show_workspace' | 'generate_handoff' | 'current_workspace' | 'switch_workspace' | 'create_workspace'",
  "status": "'success' | 'error' (present for file operations)",
  "error": "string (present on error)",
  "...": "command-specific fields"
}
```

### ErrorContract (all endpoints)

```json
{
  "status": "'error'",
  "error": "string — human-readable error message"
}
```

---

## 3. Internal Guarantees

| Guarantee | Description |
|-----------|-------------|
| Identical input → identical output | Deterministic DAG construction and execution |
| No hidden fields | Every response field is documented or self-describing |
| No schema drift | API/CLI/UI use same field names and ordering |
| Null/missing → empty default | Optional fields always produce empty containers (empty array, empty object, zero, empty string) |
| Error → structured error | Every failure returns `{ "status": "error", "error": "..." }` |
| No raw store access | External consumers cannot query memory stores directly |
| Continuation always overrides | If continuity detects a chain, new goals merge into existing context |

---

## 4. Cross-Layer Consistency Rules

1. **Field names**: All JSON responses use `snake_case` consistently across API, CLI, and WebSocket.
2. **Ordering**: Array fields within a given lens always use the same sort order (chronological or deterministic).
3. **Fallback values**: Missing optional fields render as `null`, `[]`, `{}`, or `0` — never as a raw exception.
4. **Error structure**: All errors across all surfaces use `{ "status": "error", "error": "..." }`.
5. **Status enumeration**: The set of allowed status values (`success`, `failed`, `clarification_required`, `error`) is identical across all surfaces.
6. **Timestamp format**: All timestamps use ISO 8601 with `Z` suffix or milliseconds from epoch — never mixed.
7. **Lens identification**: The `lens` field in project view responses exactly matches the `data-lens` attribute in frontend HTML.
