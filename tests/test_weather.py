import httpx
import respx
from fastapi.testclient import TestClient

OWM = "https://api.openweathermap.org/data/2.5/weather"

OK_PAYLOAD = {
    "name": "London",
    "main": {"temp": 11.5, "humidity": 80},
    "weather": [{"main": "Clouds"}],
}


@respx.mock
def test_weather_success(client: TestClient) -> None:
    route = respx.get(OWM).mock(return_value=httpx.Response(200, json=OK_PAYLOAD))
    r = client.get("/weather", params={"city": "London"})
    assert r.status_code == 200
    assert r.json() == {
        "city": "London",
        "temperature": 11.5,
        "condition": "Clouds",
        "humidity": 80,
    }
    assert route.calls.last.request.url.params["q"] == "London"


@respx.mock
def test_weather_city_not_found(client: TestClient) -> None:
    respx.get(OWM).mock(return_value=httpx.Response(404, json={"message": "city not found"}))
    r = client.get("/weather", params={"city": "Zzzxq"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "city_not_found"


@respx.mock
def test_weather_upstream_500_is_502_after_retry(client: TestClient) -> None:
    route = respx.get(OWM).mock(return_value=httpx.Response(500))
    r = client.get("/weather", params={"city": "London"})
    assert r.status_code == 502
    assert route.call_count == 2  # one retry


@respx.mock
def test_weather_upstream_bad_key_is_502(client: TestClient) -> None:
    respx.get(OWM).mock(return_value=httpx.Response(401))
    assert client.get("/weather", params={"city": "London"}).status_code == 502


@respx.mock
def test_weather_timeout_is_502(client: TestClient) -> None:
    respx.get(OWM).mock(side_effect=httpx.ConnectTimeout("slow"))
    assert client.get("/weather", params={"city": "London"}).status_code == 502


@respx.mock
def test_weather_malformed_payload_is_502(client: TestClient) -> None:
    respx.get(OWM).mock(return_value=httpx.Response(200, json={"unexpected": True}))
    assert client.get("/weather", params={"city": "London"}).status_code == 502


def test_weather_missing_city_is_422(client: TestClient) -> None:
    assert client.get("/weather").status_code == 422


def test_weather_empty_city_is_422(client: TestClient) -> None:
    assert client.get("/weather", params={"city": ""}).status_code == 422
