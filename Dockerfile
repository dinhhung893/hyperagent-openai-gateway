FROM python:3.11-slim

WORKDIR /app

# Dependencies first for layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY gateway ./gateway

ENV GATEWAY_HOST=0.0.0.0 \
    GATEWAY_PORT=8000 \
    GATEWAY_UPSTREAM=mcp \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "gateway.app:app", "--host", "0.0.0.0", "--port", "8000"]
