import os
import certifi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# DATABASE_URL exemplo (TiDB Cloud, via PyMySQL) — SEM parâmetros ssl_verify_cert/
# ssl_verify_identity na string; o TLS é configurado no código abaixo:
# mysql+pymysql://usuario:senha@host:4000/sisgerec
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./sisgerec_local.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("mysql+pymysql"):
    # TiDB Cloud exige conexão TLS. O pymysql precisa de um contexto SSL
    # explícito (com verificação de certificado) — os parâmetros
    # ssl_verify_cert/ssl_verify_identity na URL não funcionam com pymysql.
    connect_args = {"ssl": {"ca": certifi.where()}}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=280, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
