from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from stadtfest.adapters.inbound.rest.errors import register_error_handlers
from stadtfest.adapters.inbound.rest.middleware import REQUEST_ID_HEADER, RequestContextMiddleware


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret detail that must not leak")

    @app.get("/items")
    async def items(radius_km: int = Query(ge=10, le=300)) -> dict[str, int]:
        return {"radius": radius_km}

    return app


def test_unknown_route_uses_error_format() -> None:
    response = TestClient(_app()).get("/missing")
    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "message": "Nicht mehr verfügbar."}


def test_validation_errors_list_fields() -> None:
    response = TestClient(_app()).get("/items", params={"radius_km": 5})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_failed"
    assert "radius_km" in body["fields"]


def test_unexpected_errors_do_not_leak_details() -> None:
    client = TestClient(_app(), raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
    assert response.json()["error"] == "internal_error"
    assert "secret" not in response.text


def test_request_id_is_generated_and_echoed() -> None:
    client = TestClient(_app())
    generated = client.get("/missing").headers[REQUEST_ID_HEADER]
    assert len(generated) == 32
    echoed = client.get("/missing", headers={REQUEST_ID_HEADER: "abc-12345678"})
    assert echoed.headers[REQUEST_ID_HEADER] == "abc-12345678"
    rejected = client.get("/missing", headers={REQUEST_ID_HEADER: "<script>"})
    assert rejected.headers[REQUEST_ID_HEADER] != "<script>"


def test_http_exception_headers_are_preserved() -> None:
    response = TestClient(_app()).request("TRACE", "/items")
    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
