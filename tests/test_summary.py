from fastapi.testclient import TestClient

from tests.conftest import AUTH, FakeSummarizer


def test_missing_key_is_401(client: TestClient, fake_llm: FakeSummarizer) -> None:
    r = client.post("/summary", json={"text": "hello"})
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "ApiKey"
    assert fake_llm.calls == []  # LLM never reached


def test_wrong_key_is_401(client: TestClient) -> None:
    r = client.post("/summary", json={"text": "hello"}, headers={"X-API-Key": "nope"})
    assert r.status_code == 401


def test_second_configured_key_works(client: TestClient) -> None:
    r = client.post("/summary", json={"text": "hello"}, headers={"X-API-Key": "test-key-2"})
    assert r.status_code == 200


def test_success(client: TestClient, fake_llm: FakeSummarizer) -> None:
    r = client.post("/summary", json={"text": "  Some long text.  "}, headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {"summary": "A short summary."}
    assert fake_llm.calls == ["Some long text."]  # trimmed


def test_empty_text_is_400(client: TestClient) -> None:
    assert client.post("/summary", json={"text": ""}, headers=AUTH).status_code == 400


def test_whitespace_text_is_400(client: TestClient) -> None:
    assert client.post("/summary", json={"text": "   \n "}, headers=AUTH).status_code == 400


def test_too_long_text_is_400(client: TestClient) -> None:
    r = client.post("/summary", json={"text": "x" * 101}, headers=AUTH)  # limit is 100 in tests
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_text"


def test_text_at_limit_is_ok(client: TestClient) -> None:
    assert client.post("/summary", json={"text": "x" * 100}, headers=AUTH).status_code == 200


def test_missing_text_field_is_400(client: TestClient) -> None:
    assert client.post("/summary", json={}, headers=AUTH).status_code == 400


def test_llm_failure_is_502(client: TestClient, fake_llm: FakeSummarizer) -> None:
    fake_llm.fail = True
    r = client.post("/summary", json={"text": "hello"}, headers=AUTH)
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "llm_error"
