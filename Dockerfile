FROM python:3.11-slim

WORKDIR /app

# Install the package (brings in deps + the `hyperagent-gateway` / `hga` CLI)
COPY pyproject.toml requirements.txt ./
COPY gateway ./gateway
RUN pip install --no-cache-dir .

ENV GATEWAY_HOST=0.0.0.0 \
    GATEWAY_PORT=8000 \
    GATEWAY_UPSTREAM=mcp \
    PYTHONUNBUFFERED=1

EXPOSE 8000
# Use the unified CLI; reads .env and env vars automatically.
CMD ["hyperagent-gateway", "serve", "--host", "0.0.0.0", "--port", "8000"]
