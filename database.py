import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# DATABASE_URL exemplo (TiDB Cloud, via PyMySQL):
# mysql+pymysql://usuario:senha@host:4000/sisgerec?ssl_verify_cert=true&ssl_verify_identity=true
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./sisgerec_local.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=280, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
