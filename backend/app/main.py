"""API de Qubitor (Módulo A)."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.routes import router as ai_router
from app.api.organization import router as organization_router
from app.api.routes import router
from app.config import cors_origins
from app.integrations.github.routes import router as github_router
from app.integrations.github.webhooks import router as webhooks_router


def docs_enabled() -> bool:
    """La documentación interactiva (/docs, /openapi.json) solo fuera de Render, salvo API_DOCS=true (QUB-09)."""
    return not os.getenv("RENDER") or os.getenv("API_DOCS", "").lower() == "true"


_DOCS = docs_enabled()
app = FastAPI(
    title="Qubitor API",
    docs_url="/docs" if _DOCS else None,
    redoc_url="/redoc" if _DOCS else None,
    openapi_url="/openapi.json" if _DOCS else None,
)
app.include_router(router)
app.include_router(organization_router)
app.include_router(github_router)
app.include_router(ai_router)
app.include_router(webhooks_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Lo consultan el keep-alive y Better Stack: no depende de Redis ni de la base."""
    return {"status": "ok"}
