from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.http.app import REQUEST_ID_HEADER, create_app
from app.http.settings import Settings


def glue_with(router):
    return {
        "providers": [],
        "middleware": [],
        "routes": [{"id": "r", "mount": lambda app: app.include_router(router)}],
    }


def make(glue=None, **settings):
    return create_app(glue or {"providers": [], "middleware": [], "routes": []}, Settings(**settings))


def test_assembles_providers_middleware_and_routes_from_the_glue():
    seen = []
    router = APIRouter()

    @router.get("/ping")
    def ping():
        return {"ok": True}

    def provider(app):
        seen.append("provider")
        app.state.flag = "set"

    glue = {
        "providers": [{"id": "p", "register": provider}],
        "middleware": [],
        "routes": [{"id": "r", "mount": lambda app: app.include_router(router)}],
    }
    app = make(glue)
    assert seen == ["provider"]
    assert app.state.flag == "set"
    assert TestClient(app).get("/ping").json() == {"ok": True}


def test_middleware_is_applied_outer_to_inner_as_listed():
    order = []

    def entry(name):
        def handler(app):
            @app.middleware("http")
            async def mw(request, call_next):
                order.append(f"{name}:in")
                response = await call_next(request)
                order.append(f"{name}:out")
                return response

        return {"id": name, "handler": handler}

    router = APIRouter()
    router.add_api_route("/x", lambda: {})
    glue = {**glue_with(router), "middleware": [entry("outer"), entry("inner")]}
    TestClient(make(glue)).get("/x")
    assert order == ["outer:in", "inner:in", "inner:out", "outer:out"]


def test_duplicate_ids_are_rejected():
    glue = {
        "providers": [],
        "middleware": [],
        "routes": [
            {"id": "a", "mount": lambda app: None},
            {"id": "a", "mount": lambda app: None},
        ],
    }
    try:
        make(glue)
    except ValueError as err:
        assert 'duplicate route id "a"' in str(err)
    else:
        raise AssertionError("expected ValueError")


def test_unknown_route_uses_the_error_envelope():
    r = TestClient(make()).get("/nope")
    assert r.status_code == 404
    assert r.json() == {"error": "not-found"}


def test_http_errors_use_the_error_envelope():
    router = APIRouter()

    @router.get("/denied")
    def denied():
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="forbidden")

    r = TestClient(make(glue_with(router))).get("/denied")
    assert r.status_code == 403
    assert r.json() == {"error": "forbidden"}


def test_validation_errors_are_422_in_the_envelope_and_do_not_echo_input():
    router = APIRouter()

    class Body(BaseModel):
        age: int

    @router.post("/people")
    def create(body: Body):
        return body

    client = TestClient(make(glue_with(router)))
    r = client.post("/people", json={"age": "secret-value"})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validation-error"
    assert body["details"][0]["loc"] == ["body", "age"]
    assert "secret-value" not in r.text


def test_unhandled_errors_are_500_and_never_leak_internals():
    router = APIRouter()

    @router.get("/boom")
    def boom():
        raise RuntimeError("database password is hunter2")

    client = TestClient(make(glue_with(router)), raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    assert r.json() == {"error": "internal-error"}
    assert "hunter2" not in r.text


def test_docs_only_in_development():
    assert TestClient(make(env="development")).get("/docs").status_code == 200
    assert TestClient(make(env="development")).get("/openapi.json").status_code == 200
    prod = TestClient(make(env="production"))
    for url in ("/docs", "/redoc", "/openapi.json"):
        assert prod.get(url).status_code == 404


def test_request_id_is_generated_and_a_safe_incoming_one_is_echoed():
    client = TestClient(make())
    generated = client.get("/nope").headers[REQUEST_ID_HEADER]
    assert len(generated) >= 16
    assert client.get("/nope", headers={REQUEST_ID_HEADER: "abc-123"}).headers[REQUEST_ID_HEADER] == "abc-123"
    unsafe = client.get("/nope", headers={REQUEST_ID_HEADER: "a b<script>"}).headers[REQUEST_ID_HEADER]
    assert unsafe != "a b<script>"


def test_cors_headers_only_for_configured_origins():
    client = TestClient(make(cors_origins="https://app.example.com"))
    ok = client.get("/nope", headers={"Origin": "https://app.example.com"})
    assert ok.headers["access-control-allow-origin"] == "https://app.example.com"
    other = client.get("/nope", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in other.headers
    assert (
        "access-control-allow-origin"
        not in TestClient(make()).get("/nope", headers={"Origin": "https://app.example.com"}).headers
    )
