from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from decimal import Decimal, InvalidOperation
from database import get_db
from auth import exigir_login, exigir_perfil
from utils import calcular_saldos
import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/recursos")
def listar_recursos(request: Request, nd: str = None, origem_id: int = None,
                     usuario=Depends(exigir_login), db: Session = Depends(get_db)):
    saldos = calcular_saldos(db)
    origens = db.query(models.Origem).filter(models.Origem.ativo == True).order_by(models.Origem.nome).all()

    matriz = []
    for n in models.ND_CHOICES:
        linha = {"nd": n, "celulas": []}
        for o in origens:
            linha["celulas"].append({"origem": o, "saldo": saldos.get((n, o.id), Decimal("0"))})
        matriz.append(linha)

    q = db.query(models.Recurso)
    if nd:
        q = q.filter(models.Recurso.nd == nd)
    if origem_id:
        q = q.filter(models.Recurso.origem_id == origem_id)
    lancamentos = q.order_by(models.Recurso.data_cadastro.desc()).all()

    return templates.TemplateResponse("recursos.html", {
        "request": request, "usuario": usuario, "matriz": matriz, "origens": origens,
        "lancamentos": lancamentos, "nd_choices": models.ND_CHOICES,
        "filtro_nd": nd, "filtro_origem": origem_id,
    })


@router.get("/recursos/novo")
def novo_recurso_form(request: Request, usuario=Depends(exigir_perfil("ADMIN")),
                       db: Session = Depends(get_db)):
    origens = db.query(models.Origem).filter(models.Origem.ativo == True).order_by(models.Origem.nome).all()
    return templates.TemplateResponse("recurso_form.html", {
        "request": request, "usuario": usuario, "origens": origens,
        "nd_choices": models.ND_CHOICES, "recurso": None, "erro": None,
    })


@router.post("/recursos/novo")
def criar_recurso(request: Request, nd: str = Form(...), origem_id: int = Form(...),
                   valor: str = Form(...), observacoes: str = Form(""),
                   usuario=Depends(exigir_perfil("ADMIN")), db: Session = Depends(get_db)):
    try:
        valor_dec = Decimal(valor.replace(",", "."))
    except InvalidOperation:
        origens = db.query(models.Origem).filter(models.Origem.ativo == True).all()
        return templates.TemplateResponse("recurso_form.html", {
            "request": request, "usuario": usuario, "origens": origens,
            "nd_choices": models.ND_CHOICES, "recurso": None, "erro": "Valor inválido.",
        }, status_code=400)

    recurso = models.Recurso(nd=nd, origem_id=origem_id, valor=valor_dec,
                              observacoes=observacoes, cadastrado_por_nip=usuario.nip)
    db.add(recurso)
    db.commit()
    return RedirectResponse("/recursos", status_code=303)


@router.get("/recursos/{recurso_id}/editar")
def editar_recurso_form(recurso_id: int, request: Request, usuario=Depends(exigir_perfil("ADMIN")),
                         db: Session = Depends(get_db)):
    recurso = db.get(models.Recurso, recurso_id)
    origens = db.query(models.Origem).filter(models.Origem.ativo == True).all()
    return templates.TemplateResponse("recurso_form.html", {
        "request": request, "usuario": usuario, "origens": origens,
        "nd_choices": models.ND_CHOICES, "recurso": recurso, "erro": None,
    })


@router.post("/recursos/{recurso_id}/editar")
def editar_recurso(recurso_id: int, request: Request, nd: str = Form(...), origem_id: int = Form(...),
                    valor: str = Form(...), observacoes: str = Form(""),
                    usuario=Depends(exigir_perfil("ADMIN")), db: Session = Depends(get_db)):
    recurso = db.get(models.Recurso, recurso_id)
    recurso.nd = nd
    recurso.origem_id = origem_id
    recurso.valor = Decimal(valor.replace(",", "."))
    recurso.observacoes = observacoes
    db.commit()
    return RedirectResponse("/recursos", status_code=303)


@router.post("/recursos/{recurso_id}/excluir")
def excluir_recurso(recurso_id: int, usuario=Depends(exigir_perfil("ADMIN")), db: Session = Depends(get_db)):
    recurso = db.get(models.Recurso, recurso_id)
    if recurso:
        db.delete(recurso)
        db.commit()
    return RedirectResponse("/recursos", status_code=303)


# ---- Origens ----

@router.get("/origens")
def listar_origens(request: Request, usuario=Depends(exigir_perfil("ADMIN")), db: Session = Depends(get_db)):
    origens = db.query(models.Origem).order_by(models.Origem.nome).all()
    return templates.TemplateResponse("origens.html", {"request": request, "usuario": usuario, "origens": origens})


@router.post("/origens/nova")
def criar_origem(nome: str = Form(...), usuario=Depends(exigir_perfil("ADMIN")), db: Session = Depends(get_db)):
    if nome.strip():
        db.add(models.Origem(nome=nome.strip()))
        db.commit()
    return RedirectResponse("/origens", status_code=303)


@router.post("/origens/{origem_id}/toggle")
def toggle_origem(origem_id: int, usuario=Depends(exigir_perfil("ADMIN")), db: Session = Depends(get_db)):
    origem = db.get(models.Origem, origem_id)
    if origem:
        origem.ativo = not origem.ativo
        db.commit()
    return RedirectResponse("/origens", status_code=303)
