"""OpenAI-shaped error envelope helpers."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from fastapi.responses import JSONResponse


def error_body(message: str, type_: str = "invalid_request_error",
               param: Optional[str] = None, code: Optional[str] = None) -> dict:
    return {"error": {"message": message, "type": type_, "param": param, "code": code}}


def oai_error(status: int, message: str, type_: str = "invalid_request_error",
              param: Optional[str] = None, code: Optional[str] = None) -> JSONResponse:
    return JSONResponse(status_code=status, content=error_body(message, type_, param, code))


class OAIError(HTTPException):
    """Raise anywhere; the app-level handler renders the OpenAI envelope."""

    def __init__(self, status: int, message: str, type_: str = "invalid_request_error",
                 param: Optional[str] = None, code: Optional[str] = None):
        super().__init__(status_code=status, detail=error_body(message, type_, param, code))


def not_implemented(feature: str, hint: str = "") -> OAIError:
    msg = f"{feature} is not supported by the Hyperagent upstream (MCP surface)."
    if hint:
        msg += " " + hint
    return OAIError(501, msg, type_="invalid_request_error", code="unsupported_feature")
