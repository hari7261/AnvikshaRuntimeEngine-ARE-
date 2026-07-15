"""Self-hostable FastAPI platform adapter for the Anviksha Runtime Engine."""
# mypy: disable-error-code="misc,untyped-decorator"
from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict, deque
from collections.abc import AsyncGenerator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic, time
from typing import Any, cast
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse

from anviksha.evaluation import EvaluationCase, run_evaluation
from anviksha.exceptions import AnvikshaError, CapabilityError, PlanningError, PolicyViolationError
from anviksha.sdk.runtime import Runtime, RuntimeConfig
from anviksha.types import ExecutionConstraints, RuntimeResponse

API_KEY_HEADER = "x-api-key"
REQUEST_ID_HEADER = "x-request-id"
IDEMPOTENCY_KEY_HEADER = "idempotency-key"
TENANT_HEADER = "x-anviksha-tenant"
PROJECT_HEADER = "x-anviksha-project"
SESSION_HEADER = "x-anviksha-session-id"


@dataclass(slots=True)
class ServerMetrics:
    requests_total: int = 0
    requests_in_flight: int = 0
    executions_total: int = 0
    jobs_total: int = 0
    errors_total: int = 0
    started_at: float = field(default_factory=time)


@dataclass(slots=True)
class PlatformState:
    runtime: Runtime
    job_store_path: Path | None = None
    metrics: ServerMetrics = field(default_factory=ServerMetrics)
    idempotency: dict[str, RuntimeResponsePayload] = field(default_factory=dict)
    jobs: dict[str, JobPayload] = field(default_factory=dict)
    sessions: dict[str, SessionPayload] = field(default_factory=dict)
    rate_limits: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))


class ConstraintsPayload(BaseModel):
    """HTTP representation of runtime execution constraints."""

    max_latency_ms: int | None = None
    max_cost: float | None = None
    min_confidence: float = 0.0
    offline_only: bool = False
    allowed_capabilities: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    def to_runtime(self, context: RequestContext) -> ExecutionConstraints:
        metadata = {
            **self.metadata,
            "request_id": context.request_id,
            "tenant_id": context.tenant_id,
            "project_id": context.project_id,
            "session_id": context.session_id,
        }
        return ExecutionConstraints(
            max_latency_ms=self.max_latency_ms,
            max_cost=self.max_cost,
            min_confidence=self.min_confidence,
            offline_only=self.offline_only,
            allowed_capabilities=(
                frozenset(self.allowed_capabilities)
                if self.allowed_capabilities is not None
                else None
            ),
            metadata=metadata,
        )


class ExecutePayload(BaseModel):
    """Request body for executing a goal through the runtime."""

    goal: str = Field(min_length=1)
    inputs: dict[str, Any] = Field(default_factory=dict)
    constraints: ConstraintsPayload = Field(default_factory=ConstraintsPayload)
    session_id: str | None = None

    model_config = ConfigDict(extra="forbid")


class RequestContext(BaseModel):
    request_id: str
    tenant_id: str
    project_id: str
    session_id: str | None = None
    idempotency_key: str | None = None


class RuntimeResponsePayload(BaseModel):
    """Stable JSON response emitted by the FastAPI adapter."""

    execution_id: str
    status: str
    output: Any
    confidence: float
    metadata: dict[str, Any]
    diagnostics: list[str]
    request_id: str
    tenant_id: str
    project_id: str
    session_id: str | None = None
    cached: bool = False


class JobPayload(BaseModel):
    job_id: str
    status: str
    request_id: str
    tenant_id: str
    project_id: str
    session_id: str | None = None
    execution_id: str | None = None
    response: RuntimeResponsePayload | None = None
    error: str | None = None
    created_at: float
    updated_at: float


class SessionPayload(BaseModel):
    session_id: str
    tenant_id: str
    project_id: str
    execution_ids: list[str] = Field(default_factory=list)
    job_ids: list[str] = Field(default_factory=list)
    updated_at: float


class CapabilityPayload(BaseModel):
    """Public capability metadata returned by the server adapter."""

    id: str
    name: str
    kind: str
    supported_intents: list[str]
    deterministic: bool
    average_latency_ms: int
    cost_per_call: float


class HealthPayload(BaseModel):
    status: str
    service: str = "anviksha-runtime"


class ReadyPayload(BaseModel):
    status: str
    capabilities: int
    uptime_s: int


class JobAcceptedPayload(BaseModel):
    job_id: str
    status: str
    request_id: str
    tenant_id: str
    project_id: str
    session_id: str | None = None
    location: str


class RuntimeMiddleware(BaseHTTPMiddleware):
    """Optional auth, tenant scoping, request IDs, metrics, and rate limiting."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        state = _platform(request.app)
        state.metrics.requests_total += 1
        state.metrics.requests_in_flight += 1
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        request.state.request_id = request_id
        request.state.tenant_id = request.headers.get(TENANT_HEADER, "default")
        request.state.project_id = request.headers.get(PROJECT_HEADER, "default")
        try:
            auth_error = _auth_error(request)
            if auth_error is not None:
                state.metrics.errors_total += 1
                response: StarletteResponse = auth_error
            else:
                rate_error = _rate_limit_error(request, state)
                if rate_error is not None:
                    state.metrics.errors_total += 1
                    response = rate_error
                else:
                    response = await call_next(request)
        except Exception:
            state.metrics.errors_total += 1
            raise
        finally:
            state.metrics.requests_in_flight -= 1
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[TENANT_HEADER] = request.state.tenant_id
        response.headers[PROJECT_HEADER] = request.state.project_id
        return response


def create_app(
    runtime: Runtime | None = None,
    *,
    config: RuntimeConfig | None = None,
    title: str = "Anviksha Runtime Engine",
    version: str = "1.1.0",
) -> FastAPI:
    """Create a self-hostable FastAPI app around an Anviksha runtime.

    The adapter is still GitHub/PyPI friendly: users install it, own deployment,
    and can opt into API-key auth, rate limits, tenant/project headers,
    idempotency keys, job polling, session tracking, and metrics without an
    Anviksha-managed cloud service.
    """

    app = FastAPI(
        title=title,
        version=version,
        summary="Self-hostable adaptive AI execution runtime.",
    )
    app.state.platform = PlatformState(
        runtime=runtime or Runtime(config=config or _config_from_env()),
        job_store_path=_job_store_path_from_env(),
    )
    _load_jobs(app.state.platform)
    app.add_middleware(RuntimeMiddleware)

    @app.get("/healthz", response_model=HealthPayload, tags=["system"])
    async def healthz() -> HealthPayload:
        return HealthPayload(status="ok")

    @app.get("/readyz", response_model=ReadyPayload, tags=["system"])
    async def readyz(request: Request) -> ReadyPayload:
        state = _platform(request.app)
        return ReadyPayload(
            status="ready",
            capabilities=len(state.runtime.registry.all()),
            uptime_s=int(time() - state.metrics.started_at),
        )

    @app.get("/metrics", response_class=PlainTextResponse, tags=["system"])
    async def metrics(request: Request) -> str:
        state = _platform(request.app)
        return _metrics_text(state)

    @app.get("/dashboard", response_class=PlainTextResponse, tags=["system"])
    async def dashboard(request: Request) -> str:
        state = _platform(request.app)
        return (
            "Anviksha Runtime Dashboard\n"
            f"requests={state.metrics.requests_total}\n"
            f"executions={state.metrics.executions_total}\n"
            f"jobs={len(state.jobs)}\n"
            f"sessions={len(state.sessions)}\n"
            f"capabilities={len(state.runtime.registry.all())}\n"
        )

    @app.get("/capabilities", response_model=list[CapabilityPayload], tags=["runtime"])
    async def capabilities(request: Request) -> list[CapabilityPayload]:
        state = _platform(request.app)
        return [
            CapabilityPayload(
                id=cap.metadata.id,
                name=cap.metadata.name,
                kind=cap.metadata.kind.value,
                supported_intents=sorted(intent.value for intent in cap.metadata.supported_intents),
                deterministic=cap.metadata.deterministic,
                average_latency_ms=cap.metadata.average_latency_ms,
                cost_per_call=cap.metadata.cost_per_call,
            )
            for cap in state.runtime.registry.all()
        ]

    @app.post("/execute", response_model=RuntimeResponsePayload, tags=["runtime"])
    async def execute(
        payload: ExecutePayload,
        request: Request,
        response: Response,
        idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_KEY_HEADER),
        session_header: str | None = Header(default=None, alias=SESSION_HEADER),
    ) -> RuntimeResponsePayload:
        state = _platform(request.app)
        context = _context(request, payload, idempotency_key, session_header)
        cache_key = _cache_key(context)
        if cache_key and cache_key in state.idempotency:
            cached = cast(
                RuntimeResponsePayload,
                state.idempotency[cache_key].model_copy(update={"cached": True}),
            )
            response.headers["x-anviksha-cache"] = "hit"
            return cached
        try:
            runtime_response = await state.runtime.aexecute(
                payload.goal,
                inputs=payload.inputs,
                constraints=payload.constraints.to_runtime(context),
            )
        except (PlanningError, PolicyViolationError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except CapabilityError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except AnvikshaError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        state.metrics.executions_total += 1
        result = _response_payload(runtime_response, context)
        if cache_key:
            state.idempotency[cache_key] = result
            response.headers["x-anviksha-cache"] = "stored"
        _record_session(state, context, execution_id=result.execution_id)
        return result

    @app.post("/stream", tags=["runtime"])
    async def stream(
        payload: ExecutePayload,
        request: Request,
        idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_KEY_HEADER),
        session_header: str | None = Header(default=None, alias=SESSION_HEADER),
    ) -> StreamingResponse:
        state = _platform(request.app)
        context = _context(request, payload, idempotency_key, session_header)

        async def events() -> AsyncGenerator[str, None]:
            try:
                async for output in state.runtime.astream(
                    payload.goal,
                    inputs=payload.inputs,
                    constraints=payload.constraints.to_runtime(context),
                ):
                    yield json.dumps(
                        {"type": "chunk", "request_id": context.request_id, "output": output},
                        default=str,
                    ) + "\n"
                state.metrics.executions_total += 1
                yield json.dumps({"type": "completed", "request_id": context.request_id}) + "\n"
            except AnvikshaError as exc:
                state.metrics.errors_total += 1
                yield json.dumps(
                    {"type": "error", "request_id": context.request_id, "error": str(exc)}
                ) + "\n"

        return StreamingResponse(events(), media_type="application/x-ndjson")

    @app.post("/evaluations/smoke", tags=["evaluations"])
    async def smoke_evaluation(request: Request) -> dict[str, Any]:
        state = _platform(request.app)
        report = await run_evaluation(
            state.runtime,
            (
                EvaluationCase("calculator", "2 + 3 * 4", 14.0),
                EvaluationCase("python", "evaluate sum(range(5))", 10),
            ),
        )
        return {
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "results": [
                {
                    "name": result.name,
                    "passed": result.passed,
                    "output": result.output,
                    "expected_output": result.expected_output,
                    "diagnostics": list(result.diagnostics),
                    "error": result.error,
                }
                for result in report.results
            ],
        }

    @app.post("/jobs", response_model=JobAcceptedPayload, status_code=202, tags=["jobs"])
    async def create_job(
        payload: ExecutePayload,
        request: Request,
        idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_KEY_HEADER),
        session_header: str | None = Header(default=None, alias=SESSION_HEADER),
    ) -> JobAcceptedPayload:
        state = _platform(request.app)
        context = _context(request, payload, idempotency_key, session_header)
        job_id = str(uuid4())
        now = time()
        job = JobPayload(
            job_id=job_id,
            status="queued",
            request_id=context.request_id,
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            session_id=context.session_id,
            created_at=now,
            updated_at=now,
        )
        state.jobs[job_id] = job
        state.metrics.jobs_total += 1
        _record_session(state, context, job_id=job_id)
        _persist_jobs(state)
        asyncio.create_task(_run_job(state, job_id, payload, context))
        return JobAcceptedPayload(
            job_id=job_id,
            status="queued",
            request_id=context.request_id,
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            session_id=context.session_id,
            location=f"/jobs/{job_id}",
        )

    @app.get("/jobs/{job_id}", response_model=JobPayload, tags=["jobs"])
    async def get_job(job_id: str, request: Request) -> JobPayload:
        job = _platform(request.app).jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        _assert_scope(request, job.tenant_id, job.project_id)
        return job

    @app.delete("/jobs/{job_id}", response_model=JobPayload, tags=["jobs"])
    async def cancel_job(job_id: str, request: Request) -> JobPayload:
        state = _platform(request.app)
        job = state.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        _assert_scope(request, job.tenant_id, job.project_id)
        if job.status in {"queued", "running"}:
            job = job.model_copy(update={"status": "canceled", "updated_at": time()})
            state.jobs[job_id] = job
            _persist_jobs(state)
        return job

    @app.get("/sessions/{session_id}", response_model=SessionPayload, tags=["sessions"])
    async def get_session(session_id: str, request: Request) -> SessionPayload:
        session = _platform(request.app).sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        _assert_scope(request, session.tenant_id, session.project_id)
        return session

    return app


async def _run_job(
    state: PlatformState,
    job_id: str,
    payload: ExecutePayload,
    context: RequestContext,
) -> None:
    job = state.jobs[job_id].model_copy(update={"status": "running", "updated_at": time()})
    state.jobs[job_id] = job
    _persist_jobs(state)
    try:
        runtime_response = await state.runtime.aexecute(
            payload.goal,
            inputs=payload.inputs,
            constraints=payload.constraints.to_runtime(context),
        )
        state.metrics.executions_total += 1
        response = _response_payload(runtime_response, context)
        state.jobs[job_id] = job.model_copy(
            update={
                "status": "succeeded",
                "execution_id": response.execution_id,
                "response": response,
                "updated_at": time(),
            }
        )
        _record_session(state, context, execution_id=response.execution_id)
        _persist_jobs(state)
    except AnvikshaError as exc:
        state.metrics.errors_total += 1
        state.jobs[job_id] = job.model_copy(
            update={"status": "failed", "error": str(exc), "updated_at": time()}
        )
        _persist_jobs(state)


def _auth_error(request: Request) -> StarletteResponse | None:
    required_key = os.getenv("ANVIKSHA_SERVER_API_KEY", "")
    if not required_key:
        return None
    supplied = request.headers.get(API_KEY_HEADER, "")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        supplied = auth[7:]
    if supplied == required_key:
        return None
    return PlainTextResponse("unauthorized", status_code=401)


def _rate_limit_error(request: Request, state: PlatformState) -> StarletteResponse | None:
    limit = int(os.getenv("ANVIKSHA_SERVER_RATE_LIMIT_PER_MINUTE", "0"))
    if limit <= 0:
        return None
    key = f"{request.state.tenant_id}:{request.client.host if request.client else 'unknown'}"
    now = monotonic()
    window = state.rate_limits[key]
    while window and now - window[0] >= 60:
        window.popleft()
    if len(window) >= limit:
        return PlainTextResponse("rate limit exceeded", status_code=429)
    window.append(now)
    return None


def _job_store_path_from_env() -> Path | None:
    value = os.getenv("ANVIKSHA_SERVER_JOB_STORE_PATH", "").strip()
    return Path(value) if value else None


def _config_from_env() -> RuntimeConfig:
    return RuntimeConfig(
        register_llm=os.getenv("ANVIKSHA_SERVER_REGISTER_LLM", "").lower()
        in {"1", "true", "yes", "on"}
    )


def _platform(app: FastAPI) -> PlatformState:
    return cast(PlatformState, app.state.platform)


def _context(
    request: Request,
    payload: ExecutePayload,
    idempotency_key: str | None,
    session_header: str | None,
) -> RequestContext:
    return RequestContext(
        request_id=cast(str, request.state.request_id),
        tenant_id=cast(str, request.state.tenant_id),
        project_id=cast(str, request.state.project_id),
        session_id=payload.session_id or session_header,
        idempotency_key=idempotency_key,
    )


def _cache_key(context: RequestContext) -> str | None:
    if not context.idempotency_key:
        return None
    return ":".join(
        [context.tenant_id, context.project_id, context.session_id or "-", context.idempotency_key]
    )


def _assert_scope(request: Request, tenant_id: str, project_id: str) -> None:
    if request.state.tenant_id != tenant_id or request.state.project_id != project_id:
        raise HTTPException(status_code=404, detail="resource not found")


def _record_session(
    state: PlatformState,
    context: RequestContext,
    *,
    execution_id: str | None = None,
    job_id: str | None = None,
) -> None:
    if not context.session_id:
        return
    session = state.sessions.get(context.session_id) or SessionPayload(
        session_id=context.session_id,
        tenant_id=context.tenant_id,
        project_id=context.project_id,
        updated_at=time(),
    )
    execution_ids = list(session.execution_ids)
    job_ids = list(session.job_ids)
    if execution_id and execution_id not in execution_ids:
        execution_ids.append(execution_id)
    if job_id and job_id not in job_ids:
        job_ids.append(job_id)
    state.sessions[context.session_id] = session.model_copy(
        update={"execution_ids": execution_ids, "job_ids": job_ids, "updated_at": time()}
    )
    _persist_jobs(state)


def _response_payload(response: RuntimeResponse, context: RequestContext) -> RuntimeResponsePayload:
    return RuntimeResponsePayload(
        execution_id=response.execution_id,
        status=response.status.value,
        output=response.output,
        confidence=response.confidence,
        metadata=_jsonable_mapping(response.metadata),
        diagnostics=list(response.diagnostics),
        request_id=context.request_id,
        tenant_id=context.tenant_id,
        project_id=context.project_id,
        session_id=context.session_id,
    )


def _jsonable_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(json.dumps(dict(value), default=str)))


def _metrics_text(state: PlatformState) -> str:
    lines = {
        "anviksha_requests_total": state.metrics.requests_total,
        "anviksha_requests_in_flight": state.metrics.requests_in_flight,
        "anviksha_executions_total": state.metrics.executions_total,
        "anviksha_jobs_total": state.metrics.jobs_total,
        "anviksha_errors_total": state.metrics.errors_total,
        "anviksha_idempotency_entries": len(state.idempotency),
        "anviksha_sessions_total": len(state.sessions),
        "anviksha_uptime_seconds": int(time() - state.metrics.started_at),
    }
    return "\n".join(f"{key} {value}" for key, value in lines.items()) + "\n"


def _persist_jobs(state: PlatformState) -> None:
    if state.job_store_path is None:
        return
    payload = {
        "jobs": [job.model_dump(mode="json") for job in state.jobs.values()],
        "sessions": [session.model_dump(mode="json") for session in state.sessions.values()],
    }
    state.job_store_path.parent.mkdir(parents=True, exist_ok=True)
    state.job_store_path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")


def _load_jobs(state: PlatformState) -> None:
    if state.job_store_path is None or not state.job_store_path.exists():
        return
    payload = json.loads(state.job_store_path.read_text(encoding="utf-8"))
    for item in payload.get("jobs", []):
        job = JobPayload.model_validate(item)
        if job.status in {"queued", "running"}:
            job = job.model_copy(
                update={
                    "status": "failed",
                    "error": "server restarted before job completed",
                    "updated_at": time(),
                }
            )
        state.jobs[job.job_id] = job
    for item in payload.get("sessions", []):
        session = SessionPayload.model_validate(item)
        state.sessions[session.session_id] = session


app = create_app()
