from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
import models


def calcular_saldos(db: Session):
    """Retorna dict {(nd, origem_id): saldo_decimal} considerando lançamentos - autorizações ratificadas."""
    saldos = {}
    for r in db.query(models.Recurso).all():
        chave = (r.nd, r.origem_id)
        saldos[chave] = saldos.get(chave, Decimal("0")) + Decimal(r.valor)

    for a in db.query(models.Autorizacao).all():
        demanda = a.demanda
        chave = (demanda.nd, a.origem_id)
        debito = Decimal(a.quantidade_autorizada) * Decimal(demanda.valor_unitario)
        saldos[chave] = saldos.get(chave, Decimal("0")) - debito

    return saldos


def saldo_nd_origem(db: Session, nd: str, origem_id: int) -> Decimal:
    saldos = calcular_saldos(db)
    return saldos.get((nd, origem_id), Decimal("0"))


def lista_status_tipo_processo(db: Session, tipo_processo: str):
    itens = (
        db.query(models.StatusConfig)
        .filter(models.StatusConfig.tipo_processo == tipo_processo)
        .order_by(models.StatusConfig.ordem)
        .all()
    )
    return [i.nome_status for i in itens]


def proximo_status(db: Session, tipo_processo: str, status_atual: str):
    """Retorna o próximo status da lista configurada, ou None se já está no último (ou lista vazia)."""
    lista = lista_status_tipo_processo(db, tipo_processo)
    if not lista:
        return None
    if status_atual not in lista:
        return lista[0]
    idx = lista.index(status_atual)
    if idx + 1 < len(lista):
        return lista[idx + 1]
    return None  # já está no último status


def eh_status_final(db: Session, tipo_processo: str, status_atual: str) -> bool:
    lista = lista_status_tipo_processo(db, tipo_processo)
    return bool(lista) and status_atual == lista[-1]
