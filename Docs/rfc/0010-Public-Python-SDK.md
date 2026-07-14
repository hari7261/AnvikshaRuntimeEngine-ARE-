# RFC-0010: Public Python SDK

**Project:** Anviksha Runtime Engine (ARE)
**Version:** RFC-0010
**Status:** Draft
**Authors:** Anviksha Core Team
**Date:** July 2026

---

# Abstract

The Public Python SDK is the primary interface between applications and the Anviksha Runtime Engine. While the runtime internally consists of planners, execution engines, capability registries, policy engines, state managers, and observability components, application developers should interact with only a small, stable, and intuitive API.

The SDK hides internal complexity while exposing a declarative programming model focused on developer intent rather than execution details. Applications describe *what* they want to accomplish, and the runtime determines *how* execution should occur.

The SDK is intentionally minimal. Every additional public API increases long-term maintenance cost and reduces architectural flexibility.

---

# Motivation

Most AI frameworks expose dozens of abstractions such as agents, chains, graphs, prompts, routers, executors, workflows, nodes, sessions, callbacks, middleware, and memory managers.

As applications grow, developers become tightly coupled to framework internals.

Anviksha follows a different philosophy.

The runtime should expose one primary abstraction:

**Execution.**

Applications should not manage planners, capability routing, retries, or execution graphs.

The runtime owns execution.

The SDK exists only to communicate developer intent.

---

# Vision

The SDK should feel as simple as using a database client.

Developers should never need to understand the runtime architecture to benefit from it.

A typical application should require only a few lines of code.

```python
from anviksha import Runtime

runtime = Runtime()

response = runtime.execute(
    goal="Summarize this document"
)
```

Everything beyond this point becomes a runtime responsibility.

The API should remain stable even as internal runtime components continue to evolve.

---

# Design Philosophy

The SDK is declarative rather than procedural.

Developers define objectives, optional constraints, and configuration preferences.

The runtime determines planning, capability selection, execution order, retries, validation, caching, observability, and response generation.

The SDK should never expose implementation details such as execution graphs, planner internals, capability routing algorithms, or policy evaluation logic.

Internal architecture must remain replaceable without affecting application code.

---

# Core Responsibilities

The Public Python SDK is responsible for receiving execution requests, validating developer input, initializing runtime configuration, managing execution sessions, exposing synchronous and asynchronous APIs, supporting streaming responses, handling runtime exceptions, and returning structured execution results.

The SDK does not perform execution planning or capability invocation.

It serves exclusively as the communication layer between applications and the runtime.

---

# Runtime API

Version 1 exposes a single primary runtime object.

Applications initialize the runtime once and reuse it throughout the application lifecycle.

The runtime accepts execution requests, applies configuration, and delegates execution to the internal runtime components.

Additional APIs remain intentionally limited to preserve long-term simplicity.

The runtime should feel predictable regardless of application size.

---

# Configuration

Runtime configuration is centralized during initialization.

Applications configure execution preferences such as runtime policies, capability providers, execution limits, observability settings, plugin registration, authentication providers, and environment-specific options.

Configuration remains independent from individual execution requests.

This separation enables consistent runtime behavior while reducing repetitive application code.

---

# Execution Interface

Execution requests describe developer intent rather than execution implementation.

Applications provide goals, inputs, optional execution constraints, and response preferences.

The runtime converts these requests into execution plans without exposing planning details.

Execution may occur synchronously, asynchronously, or as a streaming response depending on application requirements.

Regardless of execution mode, the underlying runtime lifecycle remains identical.

---

# Response Model

Every execution returns a structured runtime response.

In addition to generated output, responses may contain execution metadata including execution identifiers, execution status, latency measurements, capability usage, resource consumption, confidence indicators, runtime diagnostics, and execution traces depending on configuration.

Applications receive both the result and sufficient operational information to understand runtime behavior.

The response model remains consistent across every execution type.

---

# Error Handling

The SDK provides a standardized exception model.

Rather than exposing provider-specific errors, the runtime translates failures into consistent runtime exceptions.

Applications should never need to understand individual model provider errors or infrastructure-specific failure conditions.

Errors represent execution states rather than implementation details.

This abstraction simplifies application development while improving portability across execution environments.

---

# Async and Streaming

Version 1 provides native asynchronous execution.

Streaming responses are treated as a first-class capability rather than an optional extension.

Applications may consume partial outputs while execution continues in the background.

Streaming follows the same execution lifecycle as standard execution and remains fully observable through the runtime.

The SDK maintains a consistent programming model regardless of execution mode.

---

# Extensibility

The SDK remains intentionally small.

Advanced functionality is introduced through plugins, runtime configuration, capabilities, and policies rather than expanding the public API.

This prevents API fragmentation while allowing the runtime ecosystem to evolve independently.

The public interface should remain stable across major runtime improvements.

---

# Design Principles

The Public Python SDK follows several architectural principles.

Developer intent takes precedence over execution mechanics.

The API remains minimal.

Internal architecture remains hidden.

Execution is declarative.

Configuration is centralized.

The runtime owns execution complexity.

Every public interface should remain stable across runtime versions.

The SDK should optimize developer productivity without sacrificing architectural flexibility.

---

# Future Evolution

Future versions may introduce additional SDKs for JavaScript, Go, Java, Rust, Swift, and other languages while preserving the same execution philosophy.

Language-specific SDKs should expose equivalent concepts and maintain behavioral consistency across platforms.

Regardless of language, applications communicate with the runtime using the same declarative execution model.

---

# Conclusion

The Public Python SDK defines how developers interact with the Anviksha Runtime Engine.

Rather than exposing internal runtime components, the SDK presents a simple and stable execution interface focused entirely on developer intent.

This separation allows the runtime to evolve internally while preserving a consistent developer experience.

The SDK is intentionally small because the intelligence belongs inside the runtime, not inside the application.

The guiding principle of the Public Python SDK is:

**"Describe the goal. The runtime handles everything else."**
