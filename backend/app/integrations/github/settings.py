"""Configuración de la integración con GitHub, sin dependencias de la base ni de FastAPI.

El scan-worker la importa aunque corra sin DATABASE_URL.
"""

import os


def private_repos_enabled() -> bool:
    """Los repos privados se habilitan a mano: el worker necesita CLERK_SECRET_KEY para clonarlos."""
    return os.getenv("GITHUB_PRIVATE_REPOS", "").lower() == "true"
