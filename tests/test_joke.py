import httpx
import respx
from fastapi.testclient import TestClient

JOKE_URL = "https://official-joke-api.appspot.com/random_joke"


@respx.mock
def test_joke_success(client: TestClient) -> None:
    respx.get(JOKE_URL).mock(
        return_value=httpx.Response(
            200, json={"id": 1, "type": "general", "setup": "Why?", "punchline": "Because."}
        )
    )
    r = client.get("/joke")
    assert r.status_code == 200
    assert r.json() == {"joke": "Why? Because.", "category": "general"}


@respx.mock
def test_joke_upstream_failure_is_502(client: TestClient) -> None:
    respx.get(JOKE_URL).mock(return_value=httpx.Response(503))
    assert client.get("/joke").status_code == 502


@respx.mock
def test_joke_malformed_is_502(client: TestClient) -> None:
    respx.get(JOKE_URL).mock(return_value=httpx.Response(200, json={"nope": 1}))
    assert client.get("/joke").status_code == 502


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
