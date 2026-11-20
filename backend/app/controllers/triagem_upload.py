import uuid
from typing import Optional

from fastapi import Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config.logger import logger
from app.agent.harness import avaliar_escopo, mensagem_para_escopo, priorizar_revisao_medica_ilegivel
from app.repositories.database import DatabaseRepository, get_db
from app.repositories.storage import StoragePersistenceError, StorageRepository
from app.agent.graph import excluir_checkpoint_triagem
from app.schemas.triagem import RequisicaoTriagem, RespostaTriagem
from app.services.document_parser import DocumentParserService
from app.services.metadados_inspecao import extrair_campos_rotulados, extrair_metadados_documento
from app.services.triagem import TriagemService



async def inspecionar_extracao_documento(
    file: Optional[UploadFile] = File(None),
    documento_texto: Optional[str] = Form(None),
    tipo_arquivo: str = Form("TEXTO"),
):
    """Mostra a extração e a decisão do Harness sem gravar nem iniciar triagem clínica."""
    if file is not None:
        conteudo = await file.read()
        extensao = DocumentParserService.validar_arquivo(file, conteudo)
        (
            texto_extraido,
            tipo_detectado,
            avaliacao_visual,
            metadados_documento,
        ) = DocumentParserService.inspecionar_arquivo_com_metadados(
            conteudo=conteudo,
            extensao=extensao,
            nome_arquivo=file.filename or "documento",
        )
        tipo_arquivo = tipo_detectado
    elif documento_texto is not None:
        texto_extraido = documento_texto
        avaliacao_visual = None
        metadados_documento = extrair_metadados_documento(texto_extraido).model_dump(mode="json")
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Envie um arquivo ou texto para inspecionar a extração.",
        )

    avaliacao = priorizar_revisao_medica_ilegivel(
        avaliacao_visual or avaliar_escopo(texto_extraido)
    )
    return {
        "tipo_arquivo": tipo_arquivo,
        "texto_extraido": texto_extraido,
        "metadados_documento": metadados_documento,
        "campos_rotulados": extrair_campos_rotulados(texto_extraido),
        "escopo": avaliacao.escopo,
        "legibilidade": avaliacao.legibilidade,
        "evidencias_escopo": [item.model_dump(mode="json") for item in avaliacao.evidencias],
        "justificativa_escopo": avaliacao.justificativa,
        "persistido": False,
        "triagem_iniciada": False,
    }

async def processar_upload_triagem(
    file: Optional[UploadFile] = File(
        None,
        description="Arquivo clínico nos formatos PDF (.pdf) ou Imagem (.png, .jpg, .jpeg, .webp, .heic)",
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

    - Valida extensão e MIME-type (PDF, PNG, JPG, WebP, HEIC)
    - Limite máximo de arquivo: 10 MB
    - Extrai texto vetorial do PDF ou metadados de imagem para pipeline clínico
    - Encaminha automaticamente para classificação, extração e roteamento
    """
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo obrigatório 'file' ausente. Envie o arquivo como multipart/form-data.",
        )

    conteudo = await file.read()
    extensao = DocumentParserService.validar_arquivo(file, conteudo)
    (
        texto_extraido,
        tipo_arquivo,
        avaliacao_visual,
        metadados_documento,
    ) = DocumentParserService.inspecionar_arquivo_com_metadados(
        conteudo=conteudo,
        extensao=extensao,
        nome_arquivo=file.filename or "documento_clinico",
    )
    campos_rotulados = extrair_campos_rotulados(texto_extraido)

    doc_id = documento_id or f"DOC-UP-{uuid.uuid4().hex[:8].upper()}"
    if DatabaseRepository(db).buscar_por_documento_id(doc_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma triagem com esse identificador. Envie novamente sem informar o ID ou use outro ID.",
        )
    db.rollback()

    avaliacao = priorizar_revisao_medica_ilegivel(
        avaliacao_visual or avaliar_escopo(texto_extraido)
    )
    if avaliacao.escopo in {"nao_medico", "incerto"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=mensagem_para_escopo(avaliacao.escopo),
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
        resposta = service.processar_triagem(
            requisicao,
            referencia_fonte=info_storage.get("caminho_local"),
            avaliacao_escopo=avaliacao.model_dump(mode="json"),
            metadados_documento=metadados_documento,
            campos_rotulados=campos_rotulados,
        )
        resposta.tipo_arquivo = tipo_arquivo
        resposta.texto_extraido = texto_extraido
        resposta.metadados_documento = metadados_documento
        resposta.campos_rotulados = campos_rotulados
        resposta.escopo = avaliacao.escopo
        resposta.legibilidade = avaliacao.legibilidade
        resposta.evidencias_escopo = [
            item.model_dump(mode="json") for item in avaliacao.evidencias
        ]
        resposta.justificativa_escopo = avaliacao.justificativa
        resposta.persistido = True
        resposta.triagem_iniciada = True
        return resposta
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
