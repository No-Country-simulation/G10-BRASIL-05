from fastapi import Depends, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.orm import Session

from app.repositories.database import DatabaseRepository, get_db
from app.models.triagem import RevisaoModel
from app.services.auditoria_outbox import enfileirar_evento
from app.schemas.triagem import BloqueioAuditoriaRequest, DecisaoAuditoriaRequest
from app.services.redis_service import RedisAuditService
from app.services.triagem import TriagemService
from app.repositories.storage import StorageRepository
from app.services.autenticacao import exigir_papeis


def listar_fila_auditoria(db: Session = Depends(get_db)):
    """Lista os documentos encaminhados para a fila médica de Human-in-the-Loop."""
    repo = DatabaseRepository(db)
    docs = repo.listar_auditoria()
    resultado = []
    for doc in docs:
        try:
            created_at = (
                doc.created_at.isoformat()
                if hasattr(doc.created_at, "isoformat")
                else (str(doc.created_at) if doc.created_at else None)
            )
            resultado.append(
                {
                    "documento_id": doc.documento_id,
                    "versao": doc.versao,
                    "tipo_documento": doc.tipo_documento,
                    "score_confianca": doc.score_confianca,
                    "dados_extraidos": doc.dados_extraidos,
                    "evidencias_campos": doc.evidencias_campos,
                    "motivo_revisao": doc.motivo_revisao,
                    "etapa_revisao": doc.etapa_revisao,
                    "documento_texto": doc.documento_texto,
                    "fonte_original_disponivel": bool(doc.caminho_fonte),
                    "justificativa_roteamento": doc.justificativa_roteamento,
                    "caminho_objeto_oci": doc.caminho_objeto_oci,
                    "created_at": created_at,
                }
            )
        except Exception:
            continue
    return resultado


def baixar_fonte_original(documento_id: str, db: Session = Depends(get_db)):
    """Entrega a fonte original somente se o caminho estiver dentro do Storage do projeto."""
    doc = DatabaseRepository(db).buscar_por_documento_id(documento_id)
    if not doc or not doc.caminho_fonte:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fonte original não disponível.")

    raiz_storage = Path(StorageRepository().local_storage_dir).resolve()
    caminho = Path(doc.caminho_fonte).resolve()
    if raiz_storage not in caminho.parents or not caminho.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fonte original não disponível.")
    return FileResponse(caminho, filename=caminho.name)

def registrar_decisao_auditoria(
    documento_id: str,
    payload: DecisaoAuditoriaRequest,
    usuario=Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO")),
    db: Session = Depends(get_db),
):
    """Permite ao médico/auditor aprovar, corrigir ou rejeitar uma triagem de baixa confiança."""
    service = TriagemService(db)
    auditor_nome = getattr(usuario, "nome", None) or getattr(payload, "auditor_nome", None) or "Auditor"
    payload_validado = payload.model_copy(update={"auditor_nome": auditor_nome})
    doc_atualizado = service.registrar_decisao_medica(
        documento_id, payload_validado, revisor_id=getattr(usuario, "id", None)
    )
    if not doc_atualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento {documento_id} não encontrado na fila de auditoria.",
        )
    return {
        "mensagem": "Decisão de auditoria registrada com sucesso.",
        "documento_id": documento_id,
        "novo_status": doc_atualizado.status_processamento,
        "versao": doc_atualizado.versao,
    }

def bloquear_documento_auditoria(
    documento_id: str,
    payload: BloqueioAuditoriaRequest,
    usuario=Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO")),
    db: Session = Depends(get_db),
):
    """Adquire lock exclusivo no Redis para evitar que dois médicos auditem o mesmo laudo simultaneamente."""
    repo = DatabaseRepository(db)
    doc = repo.buscar_por_documento_id(documento_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento {documento_id} não encontrado.",
        )
    if doc.status_processamento != "EM_REVISAO_HUMANA":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O documento não está mais aguardando revisão humana.",
        )

    redis_service = RedisAuditService()
    adquiriu = redis_service.adquirir_lock(
        documento_id=documento_id,
        auditor_nome=usuario.nome,
        ttl_segundos=payload.ttl_segundos,
    )

    if not adquiriu:
        status_lock = redis_service.obter_status_lock(documento_id)
        dono = status_lock.get("auditor") or "outro médico"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Documento já está sendo auditado exclusivamente por '{dono}'.",
        )

    try:
        db.add(
            RevisaoModel(
                documento_id=doc.id,
                revisor_id=usuario.id,
                decisao="INICIADA",
                observacao=f"ttl_segundos={payload.ttl_segundos}",
            )
        )
        enfileirar_evento(
            db,
            documento=doc,
            tipo_evento="REVISAO_INICIADA",
            autor=usuario.nome,
            payload={"ttl_segundos": payload.ttl_segundos},
            incrementar_versao=False,
        )
        db.commit()
    except Exception as erro:
        db.rollback()
        try:
            redis_service.liberar_lock(documento_id=documento_id, auditor_nome=usuario.nome)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível registrar a revisão no banco; tente novamente.",
        ) from erro

    return {
        "mensagem": "Documento bloqueado com sucesso para revisão médica exclusiva.",
        "documento_id": documento_id,
        "auditor": usuario.nome,
        "bloqueado": True,
    }

def desbloquear_documento_auditoria(
    documento_id: str,
    payload: BloqueioAuditoriaRequest,
    usuario=Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO")),
    db: Session = Depends(get_db),
):
    """Libera o lock exclusivo no Redis caso o médico cancele ou finalize a revisão."""
    redis_service = RedisAuditService()
    liberou = redis_service.liberar_lock(
        documento_id=documento_id,
        auditor_nome=usuario.nome,
    )

    if not liberou:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Você não possui o lock deste documento para poder liberá-lo.",
        )

    return {
        "mensagem": "Documento desbloqueado com sucesso.",
        "documento_id": documento_id,
        "bloqueado": False,
    }

def verificar_status_lock(documento_id: str):
    """Consulta se o documento está bloqueado no Redis e quanto tempo resta de lock."""
    redis_service = RedisAuditService()
    return redis_service.obter_status_lock(documento_id)

def consultar_trilha_nosql(documento_id: str):
    """Consulta a trilha completa e imutável de eventos gravada no MongoDB (NoSQL)."""
    nosql_repo = MongoAuditoriaRepository()
    return nosql_repo.listar_por_documento(documento_id)

def listar_eventos_redis():
    """Consulta os eventos mais recentes publicados no canal de telemetria Redis."""
    redis_service = RedisAuditService()
    return redis_service.listar_eventos_recentes()
