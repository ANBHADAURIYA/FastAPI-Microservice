# ---- build stage: install dependencies into a venv ----
FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY app ./app
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir .

# ---- runtime stage: small image, non-root user ----
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
COPY --from=build /opt/venv /opt/venv
RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
# Secrets come from environment variables at `docker run --env-file .env`.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
