"""Run the gateway: python -m gateway  (or: uvicorn gateway.app:app)."""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "gateway.app:app",
        host=os.environ.get("GATEWAY_HOST", "0.0.0.0"),
        port=int(os.environ.get("GATEWAY_PORT", "8000")),
        log_level=os.environ.get("GATEWAY_LOG_LEVEL", "info"),
    )
