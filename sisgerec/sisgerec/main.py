import os
from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from auth import exigir_login, NaoAutenticado, hash_senha
import models
from routers import auth_routes, recursos, demandas, cem, status, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SisGeRec - Sistema de Gestão de Recursos")

SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax", max_age=60 * 60 * 12)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_routes.router)
app.include_router(recursos.router)
app.include_router(demandas.router)
app.include_router(cem.router)
app.include_router(status.router)
app.include_router(admin.router)


@app.exception_handler(NaoAutenticado)
async def handler_nao_autenticado(request: Request, exc: NaoAutenticado):
    return RedirectResponse("/login", status_code=303)


@app.on_event("startup")
def criar_superadmin_inicial():
    """Cria o primeiro SUPERADMIN a partir de variáveis de ambiente, se ainda não existir nenhum usuário."""
    db: Session = next(get_db())
    try:
        if db.query(models.Usuario).count() == 0:
            nip = os.environ.get("SUPERADMIN_NIP")
            senha = os.environ.get("SUPERADMIN_SENHA")
            if nip and senha:
                db.add(models.Usuario(
                    nip=nip, posto=os.environ.get("SUPERADMIN_POSTO", "CF"),
                    nome=os.environ.get("SUPERADMIN_NOME", "Administrador"),
                    setor=os.environ.get("SUPERADMIN_SETOR", "G30"),
                    perfil="SUPERADMIN", senha_hash=hash_senha(senha), ativo=True,
                ))
                db.commit()
    finally:
        db.close()


@app.get("/")
def dashboard(request: Request, usuario=Depends(exigir_login), db: Session = Depends(get_db)):
    total_demandas_pendentes = sum(
        1 for d in db.query(models.Demanda).all() if d.quantidade_pendente() > 0
    )
    total_usuarios = db.query(models.Usuario).count()
    total_linhas_status = db.query(models.LinhaStatus).count()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "usuario": usuario,
        "total_demandas_pendentes": total_demandas_pendentes,
        "total_usuarios": total_usuarios,
        "total_linhas_status": total_linhas_status,
    })
