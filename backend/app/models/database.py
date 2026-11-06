import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Utilizar el puerto 6543 para el connection pooler de Supabase
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/qubitor")

# FIX: prepare_threshold=None para Supabase (PgBouncer) y pool_pre_ping para conexiones caídas
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()