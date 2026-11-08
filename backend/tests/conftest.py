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
