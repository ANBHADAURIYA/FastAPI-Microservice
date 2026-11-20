# FastAPI Microservice

A production-style microservice exposing two external-API wrappers (weather, jokes) and an authenticated LLM summary endpoint.

## Endpoints

| Method | Path       | Description                                     |
|--------|------------|-------------------------------------------------|
| GET    | `/weather` | Query current weather by city                   |
| GET    | `/joke`    | Fetch a random joke                             |
| POST   | `/summary` | LLM text summary, `X-API-Key` header required   |
| GET    | `/health`, `/ready` | Liveness / readiness probes            |

Interactive docs: `http://localhost:8000/docs`.

### GET /weather?city=London
```json
{"city": "London", "temperature": 11.5, "condition": "Clouds", "humidity": 80}
```
`404` city not found, `502` upstream weather API failed, `422` missing/empty `city`.

### GET /joke
```json
{"joke": "Why did the chicken...? To get to the other side.", "category": "general"}
```
`502` if the upstream joke API fails.

### POST /summary
```bash
curl -X POST http://localhost:8000/summary \
  -H "X-API-Key: <your key>" -H "Content-Type: application/json" \
  -d '{"text": "Long text to summarise..."}'
```
```json
{"summary": "Two to three sentence summary."}
```

### Error matrix

| Status | When |
|--------|------|
| 400 | `/summary`: `text` empty / whitespace-only / missing / longer than `MAX_TEXT_LENGTH` |
| 401 | `/summary`: `X-API-Key` missing or invalid |
| 404 | `/weather`: city not found |
| 422 | `/weather`: `city` missing or empty |
| 429 | `/summary`: rate limit exceeded |
| 502 | Weather/joke API or LLM provider failed (timeout, 5xx, bad payload...) |

Every error has the same shape: `{"error": {"code": "...", "message": "..."}, "request_id": "..."}`.

## LLM choices (`/summary`)

- **Provider:** Anthropic Claude via the official `anthropic` SDK.
- **Model:** `claude-haiku-5-5` (small, fast, cheap, well suited to summarisation). Change with `LLM_MODEL`.
- **Style:** 2-3 concise sentences, neutral tone, same language as the input. Output capped at 300 tokens.
- **Max input length:** 10,000 characters (`MAX_TEXT_LENGTH`) to bound cost and latency.
- **Prompt-injection hardening:** the user text is wrapped in `<text>` tags and the system prompt tells the model to treat it only as content to summarise.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # then fill in the keys
uvicorn app.main:app --reload
```

Required env vars: `API_KEYS` (comma-separated), `OPENWEATHER_API_KEY`, `ANTHROPIC_API_KEY`. See `.env.example` for the optional ones. The app refuses to start if a required one is missing.

## Docker

```bash
docker build -t fastapi-microservice .
docker run --env-file .env -p 8000:8000 fastapi-microservice
```

## Tests and quality

```bash
pytest --cov=app    # no network or paid calls: upstreams mocked with respx, LLM faked
ruff check . && mypy app
```
CI (`.github/workflows/ci.yml`) runs lint, type-check, tests and a Docker build.

## Design decisions

- **Layers:** `api/routes` (HTTP only) -> `services` (business logic, upstream calls) -> `core` (config, auth, errors, logging). Services raise domain exceptions; central handlers map them to status codes.
- **Async I/O** with one pooled `httpx.AsyncClient` created at startup; explicit timeouts and one retry for transient upstream failures.
- **Auth:** keys from env, compared with `hmac.compare_digest` (constant time). Auth runs before the handler, so unauthenticated calls never reach the LLM.
- **Secrets:** only in environment variables; `httpx` URL logging is silenced because the OpenWeather key travels in the query string.
- **Rate limiting:** per API key on `/summary` (in-memory per worker; use a Redis backend for a shared limit across replicas).
- **Observability:** JSON logs, `X-Request-ID` on every response, no user text or keys in logs.
- **Known limitation:** malformed (non-JSON) bodies are rejected before the key check, so they return 400 even without a key.
