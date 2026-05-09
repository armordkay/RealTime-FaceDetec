from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.init_db import init_db


settings = get_settings()


def success(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def error(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


def create_app() -> FastAPI:
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup_event() -> None:
        init_db()
        Path(settings.media_dir).mkdir(parents=True, exist_ok=True)

    app.mount(
        settings.public_media_url,
        StaticFiles(directory=settings.media_dir),
        name="media",
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        started_at = datetime.now(timezone.utc)

        response = await call_next(request)

        elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Elapsed-MS"] = str(elapsed_ms)

        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        payload = error(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            details=[{"request_id": getattr(request.state, "request_id", None)}],
        )
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        payload = error(
            code="VALIDATION_ERROR",
            message="Invalid request",
            details=exc.errors(),
        )
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        payload = error(
            code="INTERNAL_SERVER_ERROR",
            message="Unexpected server error",
            details=[{"request_id": getattr(request.state, "request_id", None)}],
        )
        return JSONResponse(status_code=500, content=payload)

    base_router = APIRouter(prefix=settings.api_v1_prefix)

    @base_router.get("/health", tags=["system"])
    async def health_check(request: Request):
        return success(
            {
                "service": settings.app_name,
                "env": settings.app_env,
                "status": "ok",
                "request_id": getattr(request.state, "request_id", None),
            }
        )

    base_router.include_router(api_router)
    app.include_router(base_router)

    return app


app = create_app()
