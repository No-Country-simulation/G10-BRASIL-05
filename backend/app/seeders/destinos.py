from sqlalchemy.orm import Session

from app.agent.config import (
    DESTINO_ATESTADOS,
    DESTINO_ATENDIMENTO_GERAL,
    DESTINO_AUDITORIA_HUMANA,
    DESTINO_AUTORIZACOES,
    DESTINO_EMERGENCIA,
    DESTINO_EXAMES,
    DESTINO_FARMACIA,
    DESTINO_FLUXO_PADRAO,
)
from app.models.triagem import DestinoRoteamentoModel


DESTINOS_FIXOS = (
    DESTINO_ATESTADOS,
    DESTINO_ATENDIMENTO_GERAL,
    DESTINO_AUDITORIA_HUMANA,
    DESTINO_AUTORIZACOES,
    DESTINO_EMERGENCIA,
    DESTINO_EXAMES,
    DESTINO_FARMACIA,
    DESTINO_FLUXO_PADRAO,
)


def semear_destinos(db: Session) -> None:
    """Cadastros iniciais dos códigos de fila que o roteador já utiliza."""
    existentes = {
        item.codigo
        for item in db.query(DestinoRoteamentoModel.codigo)
        .filter(DestinoRoteamentoModel.codigo.in_(DESTINOS_FIXOS))
        .all()
    }
    db.add_all(
        DestinoRoteamentoModel(codigo=codigo, tipo="FILA")
        for codigo in DESTINOS_FIXOS
        if codigo not in existentes
    )
    db.flush()
