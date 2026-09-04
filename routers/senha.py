from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_usuario_logado, verificar_senha, hash_senha

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/trocar-senha")
def trocar_senha_form(request: Request, db: Session = Depends(get_db)):
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("trocar_senha.html", {
        "request": request, "usuario": usuario, "erro": None,
        "obrigatorio": usuario.deve_trocar_senha,
    })


@router.post("/trocar-senha")
def trocar_senha_submit(request: Request, senha_atual: str = Form(...),
                         nova_senha: str = Form(...), confirmar_senha: str = Form(...),
                         db: Session = Depends(get_db)):
    usuario = get_usuario_logado(request, db)
    if not usuario:
        return RedirectResponse("/login", status_code=303)

    erro = None
    if not verificar_senha(senha_atual, usuario.senha_hash):
        erro = "Senha atual incorreta."
    elif len(nova_senha) < 8:
        erro = "A nova senha deve ter pelo menos 8 caracteres."
    elif nova_senha != confirmar_senha:
        erro = "A confirmação não confere com a nova senha."

    if erro:
        return templates.TemplateResponse("trocar_senha.html", {
            "request": request, "usuario": usuario, "erro": erro,
            "obrigatorio": usuario.deve_trocar_senha,
        }, status_code=400)

    usuario.senha_hash = hash_senha(nova_senha)
    usuario.deve_trocar_senha = False
    db.commit()
    return RedirectResponse("/", status_code=303)
