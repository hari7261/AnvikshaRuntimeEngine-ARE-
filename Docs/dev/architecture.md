# Architecture

The Anviksha Runtime Engine follows Clean Architecture with strict layering:

```
┌─────────────────────────────────────────────────┐
│                   SDK (Runtime)                   │
│          execute / aexecute / astream             │
├─────────────────────────────────────────────────┤
│                   Planner                         │
│          RuleBasedPlanner → ExecutionPlan          │
├─────────────────────────────────────────────────┤
│                ExecutionEngine                     │
│     Sequential / Parallel step execution + retry   │
├─────────┬─────────┬─────────┬────────────────────┤
│Registry │ Policies│  State  │   Observability     │
│Capabi-  │Engine   │Manager  │   EventSink         │
│lities   │         │         │   OTel / InMemory   │
├─────────┴─────────┴─────────┴────────────────────┤
│                Capabilities Layer                  │
│  Calculator │ LLM │ Retrieval │ Memory │ Python   │
│  HTTP │ Filesystem │ Plugin (3rd-party)           │
└─────────────────────────────────────────────────┘
```

## Layer Responsibilities

- **SDK** — Public API surface. Wire components together.
- **Planner** — Classify intent, select capabilities, build immutable plan.
- **ExecutionEngine** — Execute plan steps with retry, parallel dispatch.
- **CapabilityRegistry** — Register, find, and filter capabilities by metadata.
- **PolicyEngine** — Validate plans and responses before/after execution.
- **StateManager** — Immutable state transition log (in-memory or SQLite).
- **Observability** — Structured event emission for debugging and monitoring.
