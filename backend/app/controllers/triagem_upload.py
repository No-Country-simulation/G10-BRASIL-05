import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config.logger import logger
from app.agent.nodes.filtro_elegibilidade import avaliar_elegibilidade
from app.repositories.database import DatabaseRepository, get_db
from app.repositories.storage import StoragePersistenceError, StorageRepository
from app.agent.graph import excluir_checkpoint_triagem
from app.schemas.triagem import RequisicaoTriagem, RespostaTriagem
from app.services.document_parser import DocumentParserService
from app.services.triagem import TriagemService

router = APIRouter(prefix="/triagem", tags=["Triagem Clínica"])

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
    if DatabaseRepository(db).buscar_por_documento_id(doc_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma triagem com esse identificador. Envie novamente sem informar o ID ou use outro ID.",
        )
    db.rollback()

    elegibilidade, _, justificativa = avaliar_elegibilidade(texto_extraido)
    if elegibilidade == "nao_medico":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O documento enviado não é médico. O processamento foi recusado.",
        )

    try:
        storage_repo = StorageRepository()
        info_storage = storage_repo.salvar_arquivo_original(
            documento_id=doc_id,
            conteudo=conteudo,
            nome_original=file.filename,
            extensao=extensao,
            mimetype=file.content_type,
        )
    except StoragePersistenceError as erro:
        logger.exception("Falha crítica ao persistir documento enviado: %s", doc_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível salvar o documento. A triagem não foi iniciada.",
        ) from erro

    logger.info(
        "Documento %s salvo em storage (%s): %s",
        doc_id,
        info_storage["status_backup"],
        info_storage["caminho_local"],
    )

    try:
        requisicao = RequisicaoTriagem(
            documento_id=doc_id,
            tipo_arquivo=tipo_arquivo,
            canal_origem=canal_origem or "Pronto_Socorro",
            documento_texto=texto_extraido,
        )
        service = TriagemService(db)
        return service.processar_triagem(
            requisicao,
            referencia_fonte=info_storage.get("caminho_local"),
        )
    except Exception:
        storage_repo.rollback_tentativa(
            caminho_fonte=info_storage.get("caminho_local"),
            objetos_oci=[info_storage.get("caminho_objeto_fonte")],
        )
        try:
            excluir_checkpoint_triagem(doc_id)
        except Exception:
            logger.exception("Falha ao limpar checkpoint do documento %s após erro", doc_id)
        raise
