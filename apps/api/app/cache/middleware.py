"""Caches successful JSON GET responses.

The key is the caller's identity (tenant and user) plus the URL, so one user's data is never served to another;
anonymous requests share the key "anon". Register it after authentication (middleware glue, inner).
"""

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import Response
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.cache.memory import MemoryCache

MAX_BODY_BYTES = 256_000  # larger responses are passed through uncached (500 entries x 256 KB bounds the memory)
NO_STORE = re.compile(r"no-store|private", re.IGNORECASE)


class CacheSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cache_ttl_seconds: float = 30  # CACHE_TTL_SECONDS


@dataclass(frozen=True)
class CachedResponse:
    body: bytes
    media_type: str


def cache_key(request: Request) -> str:
    auth = getattr(request.state, "auth", None)
    user = getattr(auth, "user_id", None)
    tenant = getattr(auth, "tenant_id", None) or getattr(request.state, "tenant_id", None)
    who = user if isinstance(user, str) and user else "anon"
    query = f"?{request.url.query}" if request.url.query else ""
    return f"{tenant if isinstance(tenant, str) else '-'}|{who}|{request.url.path}{query}"


def _cacheable(response: Response) -> bool:
    media = response.headers.get("content-type", "")
    length = response.headers.get("content-length")
    return (
        response.status_code == 200
        and media.startswith("application/json")
        and "set-cookie" not in response.headers
        and not NO_STORE.search(response.headers.get("cache-control", ""))
        and length is not None
        and length.isdigit()
        and int(length) <= MAX_BODY_BYTES
    )


def create_cache_middleware(
    cache: MemoryCache[CachedResponse],
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    async def cached(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.method.upper() != "GET":
            return await call_next(request)
        key = cache_key(request)
        hit = cache.get(key)
        if hit is not None:
            return Response(hit.body, media_type=hit.media_type, headers={"x-cache": "hit"})
        response = await call_next(request)
        if not _cacheable(response):
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])  # type: ignore[attr-defined]
        media_type = response.headers["content-type"]
        try:
            json.loads(body)
        except ValueError:
            return Response(body, status_code=response.status_code, headers=dict(response.headers))
        cache.set(key, CachedResponse(body, media_type))
        headers = dict(response.headers)
        headers["x-cache"] = "miss"
        return Response(body, status_code=200, headers=headers)

    return cached


def cache_middleware(app: FastAPI) -> None:
    """Registered in the middleware glue (inner, after authentication)."""
    cache: MemoryCache[CachedResponse] = MemoryCache(ttl_seconds=CacheSettings().cache_ttl_seconds)
    app.state.cache = cache
    app.middleware("http")(create_cache_middleware(cache))
