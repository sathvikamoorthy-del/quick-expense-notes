from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from app.cache.memory import MemoryCache
from app.cache.middleware import MAX_BODY_BYTES, CachedResponse, cache_key, create_cache_middleware


class Auth:
    def __init__(self, user_id, tenant_id=None):
        self.user_id, self.tenant_id = user_id, tenant_id


def make(auth_header="x-user"):
    app = FastAPI()
    cache: MemoryCache[CachedResponse] = MemoryCache()
    app.middleware("http")(create_cache_middleware(cache))
    calls = {"n": 0}

    @app.middleware("http")
    async def identify(request, call_next):  # stands in for the authentication middleware (outer)
        user = request.headers.get(auth_header)
        request.state.auth = Auth(user, request.headers.get("x-tenant")) if user else None
        return await call_next(request)

    # the middleware above is added last, so it runs first (outermost): the cache sees request.state.auth

    @app.get("/data")
    def data(request: Request):
        calls["n"] += 1
        auth = request.state.auth
        return {"for": auth.user_id if auth else None, "n": calls["n"]}

    @app.get("/private")
    def private(response: Response):
        calls["n"] += 1
        response.headers["Cache-Control"] = "private"
        return {"n": calls["n"]}

    @app.get("/cookie")
    def cookie(response: Response):
        calls["n"] += 1
        response.set_cookie("s", "1")
        return {"n": calls["n"]}

    @app.get("/text")
    def text():
        return Response("plain text", media_type="text/plain")

    @app.get("/fail")
    def fail():
        calls["n"] += 1
        return Response('{"e": 1}', status_code=500, media_type="application/json")

    @app.get("/big")
    def big():
        calls["n"] += 1
        return {"blob": "x" * (MAX_BODY_BYTES + 1)}

    @app.post("/data")
    def post():
        calls["n"] += 1
        return {"posted": calls["n"]}

    return TestClient(app), cache, calls


def test_a_second_identical_get_is_served_from_the_cache_without_calling_the_handler():
    client, _cache, calls = make()
    first = client.get("/data", headers={"x-user": "u1"})
    second = client.get("/data", headers={"x-user": "u1"})
    assert first.headers["x-cache"] == "miss" and second.headers["x-cache"] == "hit"
    assert first.json() == second.json() == {"for": "u1", "n": 1}
    assert calls["n"] == 1


def test_users_and_tenants_never_share_entries():
    client, _cache, calls = make()
    a = client.get("/data", headers={"x-user": "u1", "x-tenant": "t1"}).json()
    b = client.get("/data", headers={"x-user": "u2", "x-tenant": "t1"}).json()
    c = client.get("/data", headers={"x-user": "u1", "x-tenant": "t2"}).json()
    assert (a["for"], b["for"], c["for"]) == ("u1", "u2", "u1")
    assert calls["n"] == 3


def test_the_query_string_is_part_of_the_key():
    client, _cache, calls = make()
    client.get("/data?page=1", headers={"x-user": "u1"})
    client.get("/data?page=2", headers={"x-user": "u1"})
    client.get("/data?page=1", headers={"x-user": "u1"})
    assert calls["n"] == 2


def test_anonymous_requests_share_one_key():
    client, _cache, calls = make()
    client.get("/data")
    client.get("/data")
    assert calls["n"] == 1


def test_only_successful_json_get_responses_without_private_or_cookies_are_cached():
    client, cache, calls = make()
    for path in ("/private", "/cookie", "/fail", "/text"):
        client.get(path)
        client.get(path)
    assert calls["n"] == 6  # private, cookie and fail each ran twice
    assert cache.stats().size == 0


def test_other_methods_are_not_cached():
    client, _cache, calls = make()
    client.post("/data")
    client.post("/data")
    assert calls["n"] == 2


def test_the_key_is_tenant_user_and_url():
    class State:
        auth = Auth("u1", "t1")

    class Url:
        path, query = "/x", "a=1"

    class Req:
        state, url = State(), Url()

    assert cache_key(Req()) == "t1|u1|/x?a=1"  # type: ignore[arg-type]


def test_a_response_larger_than_the_cap_is_passed_through_uncached():
    client, cache, calls = make()
    client.get("/big")
    client.get("/big")
    assert calls["n"] == 2 and cache.stats().size == 0
