from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from decimal import Decimal, InvalidOperation
from database import get_db
from auth import exigir_login
from utils import gerar_xlsx
import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/demandas")
def listar_demandas(request: Request, nd: str = None, origem_id: int = None, setor: str = None,
                     usuario=Depends(exigir_login), db: Session = Depends(get_db)):
    q = db.query(models.Demanda)
    if nd:
        q = q.filter(models.Demanda.nd == nd)
    if origem_id:
        q = q.filter(models.Demanda.origem_desejada_id == origem_id)
    if setor:
        q = q.filter(models.Demanda.setor == setor)
    demandas = q.order_by(models.Demanda.data_cadastro.desc()).all()
    origens = db.query(models.Origem).filter(models.Origem.ativo == True).order_by(models.Origem.nome).all()

    return templates.TemplateResponse("demandas.html", {
        "request": request, "usuario": usuario, "demandas": demandas, "origens": origens,
        "nd_choices": models.ND_CHOICES, "setor_choices": models.SETOR_CHOICES,
        "filtro_nd": nd, "filtro_origem": origem_id, "filtro_setor": setor,
    })


@router.get("/demandas/exportar")
def exportar_demandas(nd: str = None, origem_id: int = None, setor: str = None,
                       usuario=Depends(exigir_login), db: Session = Depends(get_db)):
    q = db.query(models.Demanda)
    if nd:
        q = q.filter(models.Demanda.nd == nd)
    if origem_id:
        q = q.filter(models.Demanda.origem_desejada_id == origem_id)
    if setor:
        q = q.filter(models.Demanda.setor == setor)
    demandas = q.order_by(models.Demanda.data_cadastro.desc()).all()

    headers = ["Data", "Descrição", "ND", "Qtd. solicitada", "Vlr Unit. (R$)", "Vlr Total (R$)",
               "Origem desejada", "Qtd. autorizada", "Status geral", "Setor", "Responsável", "Observações"]
    linhas = [
        [d.data_cadastro.strftime("%d/%m/%Y"), d.descricao, d.nd, d.quantidade,
         float(d.valor_unitario), d.valor_total(),
         d.origem_desejada.nome if d.origem_desejada else "", d.quantidade_autorizada_acumulada(),
         d.status_geral(), d.setor, d.militar_responsavel.nome_completo(), d.observacoes or ""]
        for d in demandas
    ]
    buffer = gerar_xlsx(headers, linhas, "Demandas")
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=demandas_sisgerec.xlsx"},
    )


@router.get("/demandas/nova")
def nova_demanda_form(request: Request, usuario=Depends(exigir_login), db: Session = Depends(get_db)):
    origens = db.query(models.Origem).filter(models.Origem.ativo == True).order_by(models.Origem.nome).all()
    return templates.TemplateResponse("demanda_form.html", {
        "request": request, "usuario": usuario, "origens": origens,
        "nd_choices": models.ND_CHOICES, "erro": None,
    })


@router.post("/demandas/nova")
def criar_demanda(request: Request, descricao: str = Form(...), quantidade: int = Form(...),
                   nd: str = Form(...), valor_unitario: str = Form(...),
                   origem_desejada_id: str = Form(""), observacoes: str = Form(""),
                   usuario=Depends(exigir_login), db: Session = Depends(get_db)):
    try:
        valor_dec = Decimal(valor_unitario.replace(",", "."))
        if quantidade <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        origens = db.query(models.Origem).filter(models.Origem.ativo == True).all()
        return templates.TemplateResponse("demanda_form.html", {
            "request": request, "usuario": usuario, "origens": origens,
            "nd_choices": models.ND_CHOICES, "erro": "Quantidade ou valor unitário inválido.",
        }, status_code=400)

    demanda = models.Demanda(
        descricao=descricao, quantidade=quantidade, nd=nd, valor_unitario=valor_dec,
        origem_desejada_id=int(origem_desejada_id) if origem_desejada_id else None,
        militar_responsavel_nip=usuario.nip, setor=usuario.setor, observacoes=observacoes,
    )
    db.add(demanda)
    db.commit()
    return RedirectResponse("/demandas", status_code=303)


def _pode_editar(usuario, demanda) -> bool:
    return usuario.perfil in ("ADMIN", "SUPERADMIN") or usuario.nip == demanda.militar_responsavel_nip


@router.get("/demandas/{demanda_id}/editar")
def editar_demanda_form(demanda_id: int, request: Request, usuario=Depends(exigir_login),
                         db: Session = Depends(get_db)):
    demanda = db.get(models.Demanda, demanda_id)
    if not demanda or not _pode_editar(usuario, demanda):
        return RedirectResponse("/demandas", status_code=303)

    origens = db.query(models.Origem).filter(models.Origem.ativo == True).order_by(models.Origem.nome).all()
    bloqueado = len(demanda.autorizacoes) > 0  # já tem alguma autorização: trava ND e valor unitário
    return templates.TemplateResponse("demanda_form.html", {
        "request": request, "usuario": usuario, "origens": origens,
        "nd_choices": models.ND_CHOICES, "erro": None, "demanda": demanda, "bloqueado": bloqueado,
    })


@router.post("/demandas/{demanda_id}/editar")
def editar_demanda(demanda_id: int, request: Request, descricao: str = Form(...),
                    quantidade: int = Form(...), nd: str = Form(None), valor_unitario: str = Form(None),
                    origem_desejada_id: str = Form(""), observacoes: str = Form(""),
                    usuario=Depends(exigir_login), db: Session = Depends(get_db)):
    demanda = db.get(models.Demanda, demanda_id)
    if not demanda or not _pode_editar(usuario, demanda):
        return RedirectResponse("/demandas", status_code=303)

    bloqueado = len(demanda.autorizacoes) > 0
    origens = db.query(models.Origem).filter(models.Origem.ativo == True).order_by(models.Origem.nome).all()

    ja_autorizado = demanda.quantidade_autorizada_acumulada()
    erro = None
    if quantidade <= 0 or quantidade < ja_autorizado:
        erro = f"Quantidade não pode ser menor do que a já autorizada ({ja_autorizado})."
    elif not bloqueado:
        try:
            valor_dec = Decimal(valor_unitario.replace(",", "."))
        except (InvalidOperation, AttributeError):
            erro = "Valor unitário inválido."

    if erro:
        return templates.TemplateResponse("demanda_form.html", {
            "request": request, "usuario": usuario, "origens": origens,
            "nd_choices": models.ND_CHOICES, "erro": erro, "demanda": demanda, "bloqueado": bloqueado,
        }, status_code=400)

    demanda.descricao = descricao
    demanda.quantidade = quantidade
    demanda.origem_desejada_id = int(origem_desejada_id) if origem_desejada_id else None
    demanda.observacoes = observacoes
    if not bloqueado:
        demanda.nd = nd
        demanda.valor_unitario = Decimal(valor_unitario.replace(",", "."))

    db.commit()
    return RedirectResponse(f"/demandas/{demanda.id}", status_code=303)


@router.get("/demandas/{demanda_id}")
def detalhe_demanda(demanda_id: int, request: Request, usuario=Depends(exigir_login),
                     db: Session = Depends(get_db)):
    demanda = db.get(models.Demanda, demanda_id)
    return templates.TemplateResponse("demanda_detalhe.html", {
        "request": request, "usuario": usuario, "demanda": demanda,
    })
