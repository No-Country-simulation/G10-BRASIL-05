"""Publica no Mongo eventos já confirmados na transação PostgreSQL."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import time
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import aliased

from app.config.logger import logger
from app.models.triagem import AuditoriaOutboxModel
from app.repositories.nosql_auditoria import MongoAuditoriaRepository


MAX_TENTATIVAS = 12
LEASE_SEGUNDOS = 60


def hash_payload(payload: dict) -> str:
    serializado = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def enfileirar_evento(
    db,
    *,
    documento,
    tipo_evento: str,
    autor: str,
    payload: dict,
    justificativa: str | None = None,
    incrementar_versao: bool = True,
    incrementar_sequencia: bool = True,
) -> AuditoriaOutboxModel:
    """Cria evento e sequência dentro da transação operacional do chamador."""
    if incrementar_sequencia and hasattr(documento, "ultima_sequencia"):
        documento.ultima_sequencia += 1
    if incrementar_versao and hasattr(documento, "versao"):
        documento.versao += 1
    envelope = json.loads(
        json.dumps(
            {"autor": autor, "justificativa": justificativa, "payload": payload},
            ensure_ascii=False,
            default=str,
        )
    )
    evento = AuditoriaOutboxModel(
        evento_id=uuid4(),
        documento_id=getattr(documento, "id", None),
        documento_externo_id=getattr(documento, "documento_id", None),
        sequencia=getattr(documento, "ultima_sequencia", 1),
        tipo_evento=tipo_evento,
        ocorrido_em=datetime.now(timezone.utc),
        payload=envelope,
        payload_hash=hash_payload(envelope),
    )
    db.add(evento)
    return evento


def _reivindicar():
    from app.repositories.database import SessionLocal
    agora = datetime.now(timezone.utc)
    token = uuid4()
    with SessionLocal() as db:
        anterior = aliased(AuditoriaOutboxModel)
        anterior_pendente = select(anterior.evento_id).where(
            anterior.documento_id == AuditoriaOutboxModel.documento_id,
            anterior.sequencia < AuditoriaOutboxModel.sequencia,
            anterior.status != "PUBLICADO",
        )
        evento = (
            db.query(AuditoriaOutboxModel)
            .filter(
                or_(
                    and_(
                        AuditoriaOutboxModel.status == "PENDENTE",
                        or_(AuditoriaOutboxModel.proxima_tentativa_em.is_(None), AuditoriaOutboxModel.proxima_tentativa_em <= agora),
                    ),
                    and_(AuditoriaOutboxModel.status == "EM_PUBLICACAO", AuditoriaOutboxModel.lease_ate < agora),
                ),
                ~anterior_pendente.exists(),
            )
            .order_by(AuditoriaOutboxModel.criado_em.asc())
            .with_for_update(skip_locked=True)
            .first()
        )
        if evento is None:
            db.rollback()
            return None
        # A correlação da subconsulta precisa comparar com a linha externa.
        evento.claim_token = token
        evento.lease_ate = agora + timedelta(seconds=LEASE_SEGUNDOS)
        evento.status = "EM_PUBLICACAO"
        evento.tentativas += 1
        db.commit()
        return {
            "evento_id": evento.evento_id,
            "documento_id": evento.documento_id,
            "documento_externo_id": evento.documento_externo_id,
            "sequencia": evento.sequencia,
            "tipo_evento": evento.tipo_evento,
            "ocorrido_em": evento.ocorrido_em,
            "payload": evento.payload,
            "payload_hash": evento.payload_hash,
            "claim_token": token,
            "tentativas": evento.tentativas,
        }


def _finalizar(evento: dict, *, status: str, erro: str | None = None, mongo_evento_id: str | None = None) -> None:
    from app.repositories.database import SessionLocal
    with SessionLocal() as db:
        atualizado = (
            db.query(AuditoriaOutboxModel)
            .filter_by(evento_id=evento["evento_id"], claim_token=evento["claim_token"], status="EM_PUBLICACAO")
            .one_or_none()
        )
        if atualizado is None:
            db.rollback()
            return
        atualizado.status = status
        atualizado.erro_ultimo = erro
        atualizado.mongo_evento_id = mongo_evento_id
        atualizado.lease_ate = None
        if status == "PUBLICADO":
            atualizado.publicado_em = datetime.now(timezone.utc)
            atualizado.payload = {}
        elif status == "PENDENTE":
            atualizado.proxima_tentativa_em = datetime.now(timezone.utc) + timedelta(seconds=min(2 ** atualizado.tentativas, 3600))
        db.commit()


def processar_uma_vez() -> bool:
    evento = _reivindicar()
    if evento is None:
        return False
    mongo = None
    try:
        mongo = MongoAuditoriaRepository()
        resultado = mongo.inserir_evento_idempotente(evento)
        _finalizar(evento, status="PUBLICADO", mongo_evento_id=resultado.get("_id"))
    except Exception as erro:
        permanente = getattr(erro, "integridade_outbox", False)
        status = "ERRO_INTEGRIDADE" if permanente else "PENDENTE" if evento["tentativas"] < MAX_TENTATIVAS else "ERRO"
        _finalizar(evento, status=status, erro=str(erro)[:1000])
        logger.exception("Falha ao publicar evento de auditoria no Mongo")
    finally:
        if mongo is not None:
            mongo.fechar()
    return True


def executar_worker_outbox(parada, intervalo_segundos: float = 1.0) -> None:
    """Loop cooperativo para thread do supervisor de workers."""
    while not parada.is_set():
        try:
            if not processar_uma_vez():
                parada.wait(intervalo_segundos)
        except Exception:
            logger.exception("Erro inesperado no worker do outbox Mongo")
            time.sleep(intervalo_segundos)
