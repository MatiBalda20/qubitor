"""API de Qubitor (Módulo A)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.routes import router as ai_router
from app.api.routes import router
from app.config import cors_origins
from app.integrations.github.routes import router as github_router
from app.integrations.github.webhooks import router as webhooks_router

app = FastAPI(title="Qubitor API")
app.include_router(router)
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
