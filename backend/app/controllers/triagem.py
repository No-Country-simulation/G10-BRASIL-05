import uuid
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.schemas.triagem import (
    RequisicaoTriagem,
    RespostaTriagem,
    DecisaoAuditoriaRequest,
    BloqueioAuditoriaRequest,
)
from app.repositories.database import get_db, DatabaseRepository
from app.repositories.nosql_auditoria import MongoAuditoriaRepository
from app.services.triagem import TriagemService
from app.services.redis_service import RedisAuditService
from app.services.document_parser import DocumentParserService

router = APIRouter(prefix="/triagem", tags=["Triagem Clínica"])


@router.post("", response_model=RespostaTriagem, status_code=status.HTTP_200_OK)
def processar_triagem(
    requisicao: RequisicaoTriagem,
    db: Session = Depends(get_db),
):
    """Endpoint principal de triagem: ingere documento em texto/JSON, classifica, extrai e roteia."""
    service = TriagemService(db)
    return service.processar_triagem(requisicao)


@router.post("/upload", response_model=RespostaTriagem, status_code=status.HTTP_200_OK)
async def processar_upload_triagem(
    file: UploadFile = File(
        ...,
        description="Arquivo clínico nos formatos PDF (.pdf) ou Imagem (.png, .jpg, .jpeg, .webp)",
    ),
    canal_origem: Optional[str] = Form(
        "Pronto_Socorro",
        description="Canal de entrada hospitalar (ex: Pronto_Socorro, Ambulatorio, Telemedicina)",
    ),
    documento_id: Optional[str] = Form(
        None,
        description="Identificador único opcional do documento (se omitido, será gerado automaticamente)",
    ),
    db: Session = Depends(get_db),
):
    """Endpoint multipart para ingestão de arquivos PDF e Imagens clínicas (SCRUM-67).

    - Valida extensão e MIME-type (PDF, PNG, JPG, WebP)
    - Limite máximo de arquivo: 10 MB
    - Extrai texto vetorial do PDF ou metadados de imagem para pipeline clínico
    - Encaminha automaticamente para classificação, extração e roteamento
    """
    conteudo = await file.read()
    extensao = DocumentParserService.validar_arquivo(file, conteudo)
    texto_extraido, tipo_arquivo = DocumentParserService.extrair_texto(
        conteudo=conteudo,
        extensao=extensao,
        nome_arquivo=file.filename or "documento_clinico",
    )

    doc_id = documento_id or f"DOC-UP-{uuid.uuid4().hex[:8].upper()}"

    requisicao = RequisicaoTriagem(
        documento_id=doc_id,
        tipo_arquivo=tipo_arquivo,
        canal_origem=canal_origem or "Pronto_Socorro",
        documento_texto=texto_extraido,
    )

    service = TriagemService(db)
    return service.processar_triagem(requisicao)


@router.get("/documentos", status_code=status.HTTP_200_OK)
def listar_documentos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retorna o histórico de documentos processados."""
    repo = DatabaseRepository(db)
    docs = repo.listar_todos(skip=skip, limit=limit)
    return [
        {
            "documento_id": doc.documento_id,
            "tipo_documento": doc.tipo_documento,
            "nivel_prioridade": doc.nivel_prioridade,
            "score_confianca": doc.score_confianca,
            "destino_principal": doc.destino_principal,
            "status_processamento": doc.status_processamento,
            "requer_auditoria_humana": doc.requer_auditoria_humana,
            "created_at": doc.created_at,
        }
        for doc in docs
    ]


@router.get("/auditoria", status_code=status.HTTP_200_OK)
def listar_fila_auditoria(db: Session = Depends(get_db)):
    """Lista os documentos encaminhados para a fila médica de Human-in-the-Loop."""
    repo = DatabaseRepository(db)
    docs = repo.listar_auditoria()
    return [
        {
            "documento_id": doc.documento_id,
            "tipo_documento": doc.tipo_documento,
            "score_confianca": doc.score_confianca,
            "dados_extraidos": doc.dados_extraidos,
            "justificativa_roteamento": doc.justificativa_roteamento,
            "caminho_objeto_oci": doc.caminho_objeto_oci,
            "created_at": doc.created_at,
        }
        for doc in docs
    ]


@router.post("/auditoria/{documento_id}/decisao", status_code=status.HTTP_200_OK)
def registrar_decisao_auditoria(
    documento_id: str,
    payload: DecisaoAuditoriaRequest,
    db: Session = Depends(get_db),
):
    """Permite ao médico/auditor aprovar, corrigir ou rejeitar uma triagem de baixa confiança."""
    service = TriagemService(db)
    doc_atualizado = service.registrar_decisao_medica(documento_id, payload)
    if not doc_atualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento {documento_id} não encontrado na fila de auditoria.",
        )
    return {
        "mensagem": "Decisão de auditoria registrada com sucesso.",
        "documento_id": documento_id,
        "novo_status": doc_atualizado.status_processamento,
    }


@router.post("/auditoria/{documento_id}/bloquear", status_code=status.HTTP_200_OK)
def bloquear_documento_auditoria(
    documento_id: str,
    payload: BloqueioAuditoriaRequest,
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

    redis_service = RedisAuditService()
    adquiriu = redis_service.adquirir_lock(
        documento_id=documento_id,
        auditor_nome=payload.auditor_nome,
        ttl_segundos=payload.ttl_segundos,
    )

    if not adquiriu:
        status_lock = redis_service.obter_status_lock(documento_id)
        dono = status_lock.get("auditor") or "outro médico"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Documento já está sendo auditado exclusivamente por '{dono}'.",
        )

    # Registra o evento de bloqueio na trilha NoSQL imutável
    nosql_repo = MongoAuditoriaRepository()
    nosql_repo.gravar_evento(
        documento_id=documento_id,
        tipo_evento="BLOQUEIO_EXCLUSIVO",
        autor=payload.auditor_nome,
        payload={"ttl_segundos": payload.ttl_segundos},
    )

    return {
        "mensagem": "Documento bloqueado com sucesso para revisão médica exclusiva.",
        "documento_id": documento_id,
        "auditor": payload.auditor_nome,
        "bloqueado": True,
    }


@router.post("/auditoria/{documento_id}/desbloquear", status_code=status.HTTP_200_OK)
def desbloquear_documento_auditoria(
    documento_id: str,
    payload: BloqueioAuditoriaRequest,
    db: Session = Depends(get_db),
):
    """Libera o lock exclusivo no Redis caso o médico cancele ou finalize a revisão."""
    redis_service = RedisAuditService()
    liberou = redis_service.liberar_lock(
        documento_id=documento_id,
        auditor_nome=payload.auditor_nome,
    )

    if not liberou:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Você não possui o lock deste documento para poder liberá-lo.",
        )

    nosql_repo = MongoAuditoriaRepository()
    nosql_repo.gravar_evento(
        documento_id=documento_id,
        tipo_evento="DESBLOQUEIO_AUDITORIA",
        autor=payload.auditor_nome,
        payload={},
    )

    return {
        "mensagem": "Documento desbloqueado com sucesso.",
        "documento_id": documento_id,
        "bloqueado": False,
    }


@router.get("/auditoria/{documento_id}/status-lock", status_code=status.HTTP_200_OK)
def verificar_status_lock(documento_id: str):
    """Consulta se o documento está bloqueado no Redis e quanto tempo resta de lock."""
    redis_service = RedisAuditService()
    return redis_service.obter_status_lock(documento_id)


@router.get("/auditoria/{documento_id}/trilha-nosql", status_code=status.HTTP_200_OK)
def consultar_trilha_nosql(documento_id: str):
    """Consulta a trilha completa e imutável de eventos gravada no MongoDB (NoSQL)."""
    nosql_repo = MongoAuditoriaRepository()
    return nosql_repo.listar_por_documento(documento_id)


@router.get("/auditoria/eventos-redis", status_code=status.HTTP_200_OK)
def listar_eventos_redis():
    """Consulta os eventos mais recentes publicados no canal de telemetria Redis."""
    redis_service = RedisAuditService()
    return redis_service.listar_eventos_recentes()
