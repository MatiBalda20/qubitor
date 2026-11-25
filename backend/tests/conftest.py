"""Configuración común de los tests del backend."""

import os

# app/models/database.py exige DATABASE_URL al importarse (PR #25). Los tests que
# usan una base reciben la suya con QUBITOR_TEST_DATABASE_URL; al resto le alcanza
# una URL que nunca se conecta, porque crear el engine no abre conexiones. Se
# define antes de cargar backend/.env, así los tests nunca tocan Supabase.
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv("QUBITOR_TEST_DATABASE_URL") or "postgresql+psycopg://qubitor:qubitor@127.0.0.1:1/qubitor",
)

# Lo mismo con KV y el bucket (Módulo D): con backend/.env completo, los tests
# usarían la caché y el bucket reales. Vacías, el código los da por no
# configurados. Solo el test del bucket real las necesita (QUBITOR_TESTS_BUCKET=1).
_REAL_BUCKET = os.getenv("QUBITOR_TESTS_BUCKET") == "1"
_KV = ("CF_ACCOUNT_ID", "CF_KV_NAMESPACE_ID", "CF_API_TOKEN")
_BUCKET = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET", "R2_ENDPOINT", "R2_REGION")
for variable in _KV if _REAL_BUCKET else _KV + _BUCKET:
    os.environ.setdefault(variable, "")
if _REAL_BUCKET:
    from dotenv import load_dotenv

    load_dotenv()  # trae las R2_* de backend/.env; no pisa las variables ya definidas
