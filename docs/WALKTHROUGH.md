# Project Walkthrough

## 1. The one-minute pitch

A FastAPI microservice with three endpoints:

- `GET /weather?city=` wraps OpenWeatherMap.
- `GET /joke` wraps a public joke API.
- `POST /summary` sends text to an LLM (Anthropic Claude) and returns a short summary. It requires an `X-API-Key` header.

The assignment is small, so the interesting part is how it is built: layered code, uniform error handling, authentication, rate limiting, structured logging, tests that need no network or paid calls, Docker and CI.

## 2. Architecture

```
Client
  |  HTTP
  v
Middleware: RequestId (X-Request-ID)  ->  SlowAPI (rate limit)
  v
Routes (app/api/routes)     HTTP only: parse input, call a service, return a model
  |  Depends(...)           injects settings, HTTP client, summarizer, auth check
  v
Services (app/services)     business logic + calls to external systems
  |        |         |
  v        v         v
OpenWeather  Joke API  Anthropic API

Cross-cutting (app/core): config, security, errors, logging, ratelimit
```

Rule of thumb: routes know about HTTP, services know about the outside world, and neither knows about the other's details. Services raise Python exceptions, and one central place turns them into status codes.

## 3. File map

| File | Role |
|---|---|
| `app/main.py` | Builds the app. The `lifespan` function creates one shared `httpx.AsyncClient` and the LLM client at startup and closes them at shutdown. Registers middleware, error handlers and routers. |
| `app/core/config.py` | `Settings` (pydantic-settings) reads env vars / `.env` and validates them. The app refuses to start if a required key is missing. |
| `app/core/security.py` | `require_api_key` dependency: reads `X-API-Key`, compares with `hmac.compare_digest`, raises 401. |
| `app/core/errors.py` | Exception classes (`CityNotFoundError` 404, `UpstreamError` 502, `LLMError` 502, `InvalidTextError` 400, `UnauthorizedError` 401) and the handlers that return one JSON shape. |
| `app/core/logging.py` | JSON logs and a request-id middleware. Silences httpx URL logging because the OpenWeather key is in the URL. |
| `app/core/ratelimit.py` | SlowAPI limiter keyed by API key (or IP). |
| `app/api/deps.py` | Dependency functions that hand shared objects to routes. |
| `app/api/routes/*.py` | One file per endpoint, plus health. |
| `app/schemas/*.py` | Pydantic models: the request and response contracts. |
| `app/services/http.py` | `get_json`: GET with one retry on network errors and 5xx, otherwise raises `UpstreamError`. |
| `app/services/weather_service.py`, `joke_service.py` | Call the upstream and map its response to our schema. |
| `app/services/llm_service.py` | System prompt, `AnthropicSummarizer`, and a `Summarizer` Protocol so tests can use a fake. |
| `tests/` | 25 tests with mocked upstreams. |
| `Dockerfile`, `.github/workflows/ci.yml`, `Makefile` | Packaging, CI and shortcuts. |

## 4. FastAPI concepts used (the ones to explain if asked)

- **Type hints are the contract.** `city: Annotated[str, Query(min_length=1)]` makes the parameter required and validated. Pydantic models validate JSON bodies. Bad input is rejected before our code runs.
- **Auto-generated docs.** FastAPI builds an OpenAPI spec from the code, which is why `/docs` (Swagger UI) exists. `responses={...}` on each route documents the error codes.
- **Dependency injection (`Depends`).** Reusable pieces such as the auth check, settings and HTTP client are declared as dependencies. Tests replace them with `app.dependency_overrides`, which is how the fake LLM works.
- **async/await.** Calling external APIs is waiting. `async` lets one worker serve other requests during the wait.
- **Lifespan.** Startup and shutdown code. We create one pooled HTTP client so connections are reused instead of re-opened per request.

## 5. How each endpoint works

### GET /weather
1. `city` is validated (required, 1 to 100 characters).
2. The service calls OpenWeatherMap with `units=metric`.
3. `get_json` accepts 200 and 404 as meaningful answers. A 404 becomes `CityNotFoundError`, returned as HTTP 404.
4. Any other failure (timeout, 5xx, 401, 429, malformed JSON) becomes `UpstreamError`, returned as 502.
5. The response is mapped to `{city, temperature, condition, humidity}`.

### GET /joke
Calls the joke API, builds `joke` from setup plus punchline, and uses `type` as `category`. Any failure returns 502.

### POST /summary
1. **Auth first.** The route has `dependencies=[Depends(require_api_key)]`. Missing or wrong key returns 401 and the LLM is never reached, so strangers cannot spend your money.
2. **Rate limit.** 10 requests per minute per key by default (429 when exceeded).
3. **Validation.** The text is stripped. Empty, whitespace-only, missing, or longer than 10,000 characters returns 400. FastAPI would normally return 422 for a bad body, so a custom handler maps body errors to 400 as the spec requires.
4. **LLM call.** `AnthropicSummarizer.summarize` sends a system prompt plus the user text, and returns the text of the reply.
5. Provider errors or an empty reply become `LLMError`, returned as 502.

## 6. The LLM part, explained simply

- An LLM call is: *system prompt* (standing instructions) + *user message* (the content) goes in, text comes out.
- **Provider and model:** Anthropic Claude, `claude-haiku-5-5`, a small, fast, cheap model that suits summarisation. Changeable via `LLM_MODEL`.
- **Style:** 2 to 3 concise sentences, neutral tone, same language as the input.
- **Cost and latency control:** input capped at 10,000 characters, output capped at 300 tokens, a timeout, and 2 automatic SDK retries on 429/5xx.
- **Prompt-injection hardening:** the user text is wrapped in `<text>` tags and the system prompt says to treat it only as content to summarise and never follow instructions inside it. This reduces the risk but does not eliminate it.
- **Testability:** the route depends on a `Summarizer` interface, so tests inject a fake and never call the paid API.

## 7. Error handling design

Services raise domain exceptions. Handlers in `errors.py` map them to HTTP. Every failure has the same shape:

```json
{"error": {"code": "city_not_found", "message": "..."}, "request_id": "..."}
```

| Status | Meaning |
|---|---|
| 400 | `/summary` body invalid (empty, too long, missing field) |
| 401 | missing or invalid API key |
| 404 | city not found |
| 422 | `/weather` query parameter missing or empty |
| 429 | rate limit exceeded |
| 502 | an upstream (weather, joke, LLM) failed |
| 500 | anything unexpected. The traceback goes to the logs only, never to the client. |

## 8. Security and production practices

- API keys compared in constant time (prevents timing attacks).
- Secrets only in environment variables. `.env` is gitignored, and `.env.example` is a placeholder template.
- Auth before cost: the 401 check runs before any LLM call.
- Rate limiting protects against abuse and runaway spend.
- JSON logs with a request id, also returned as the `X-Request-ID` header for tracing. No keys or user text are logged.
- Timeouts and one retry on every upstream call, so a slow provider cannot hang the service.
- Docker image: multi-stage, non-root user, health check. CI runs ruff, mypy, pytest and a Docker build.
- `/health` and `/ready` probes for orchestrators.

## 9. Testing

25 tests, no network and no paid calls:
- Upstream HTTP is mocked with `respx`. The LLM is replaced by a fake via dependency override.
- Weather: success, 404, 500 (and that it retried once), upstream 401, timeout, malformed payload, missing and empty city.
- Joke: success, upstream failure, malformed payload.
- Summary: no key, wrong key, second key, success (and text trimmed), empty, whitespace, too long, exactly at the limit, missing field, LLM failure.
- LLM service: joins text blocks, wraps input in tags, maps API errors and empty replies to `LLMError`.
- 98% line coverage. ruff and mypy (strict) are clean.

## 10. Honest limitations and next steps

- The joke provider (`official-joke-api.appspot.com`) returned 503 during testing. The service correctly returned 502, but the provider's outage means `/joke` fails until it recovers or we switch to another provider such as JokeAPI v2.
- A non-JSON body on `/summary` is rejected before the key check, so it returns 400 even without a key.
- The rate limiter is in memory per worker. With multiple replicas, use Redis.
- API keys come from env vars. At larger scale, move them to a database or secret manager with per-client keys, revocation and usage tracking.
- Not yet added: caching (for example, weather by city for a few minutes), metrics/tracing (Prometheus, OpenTelemetry), a circuit breaker, streaming summaries.
- The real LLM and OpenWeather calls were verified through mocks. A live run depends on valid keys (new OpenWeather keys can take a couple of hours to activate).

## 11. Suggested demo script (5 minutes)

1. Show `/docs` and point out it is generated from the code.
2. `/weather?city=London` gives 200. `city=Zzzxq` gives 404. Leaving `city` empty gives 422.
3. `/summary` without the key gives 401. Click **Authorize**, paste the key, and run again. Try empty text for 400, then a real paragraph for a 200 summary.
4. Show the `X-Request-ID` response header and the JSON log line in the terminal.
5. Run `pytest` and show 25 passing without any network.
6. Mention the Dockerfile and CI, then the limitations in section 10.

## 12. Likely questions

- **Why async?** The service mostly waits on other APIs. Async handles many requests per worker.
- **Why a service layer?** Routes stay thin and logic is testable without HTTP.
- **Why 502 and not 500 for upstream failures?** 502 (Bad Gateway) states that our service is fine and the dependency failed, which helps clients and monitoring.
- **Why constant-time comparison?** A normal `==` stops at the first differing character, which can leak information through response timing.
- **How do you stop LLM cost abuse?** Authentication, rate limiting, input length cap, output token cap.
- **How would you scale it?** Run multiple replicas behind a load balancer, move the rate limiter to Redis, add caching and metrics.
- **Why Claude Haiku?** Summaries are a simple task, so a small, fast, cheap model gives good quality at low cost.
