"""FastAPI application factory: assembles the scaffold's glue (providers, middleware, routes) into one app.

Glue entries are dicts (see app/glue/*.py):
  providers:  {"id", "register": callable(app)}   wiring (state, dependencies, lifespan hooks)
  middleware: {"id", "handler": callable(app)}    added outer to inner, as listed
  routes:     {"id", "mount": callable(app)}      usually app.include_router(router)
"""

import logging
import re
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.http.settings import Settings, get_settings

log = logging.getLogger("app")
REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _assert_unique(kind: str, entries: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for entry in entries:
        if entry["id"] in seen:
            raise ValueError(f'duplicate {kind} id "{entry["id"]}"')
        seen.add(entry["id"])


def load_glue() -> dict[str, list[dict[str, Any]]]:
    from app.glue.middleware import middleware
    from app.glue.providers import providers
    from app.glue.routes import routes

    return {"providers": providers, "middleware": middleware, "routes": routes}


def error_body(code: str, **extra: Any) -> dict[str, Any]:
    """The project error envelope: {"error": "<code or message>"} plus optional details."""
    return {"error": code, **extra}


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Echoes a safe incoming X-Request-ID or generates one; kept on request.state.request_id."""

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Any:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not-found" if exc.status_code == 404 and exc.detail == "Not Found" else str(exc.detail)
        return JSONResponse(error_body(code), status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # loc, msg and type only: never echo the submitted input back
        details = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(error_body("validation-error", details=details), status_code=422)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception(
            "unhandled error",
            extra={"request_id": getattr(request.state, "request_id", None)},
        )
        return JSONResponse(error_body("internal-error"), status_code=500)  # never leak internals


def create_app(
    glue: dict[str, list[dict[str, Any]]] | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    glue = glue if glue is not None else load_glue()
    settings = settings or get_settings()
    for kind in ("providers", "middleware", "routes"):
        _assert_unique(kind.rstrip("s"), glue.get(kind, []))

    docs = settings.is_development
    app = FastAPI(
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    _install_error_handlers(app)
    for provider in glue.get("providers", []):
        provider["register"](app)
    # Starlette makes the LAST added middleware the outermost, so add in reverse: the first listed ends outermost.
    for entry in reversed(glue.get("middleware", [])):
        entry["handler"](app)
    app.add_middleware(RequestIdMiddleware)
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=[REQUEST_ID_HEADER],
        )
    for route in glue.get("routes", []):
        route["mount"](app)
    return app
