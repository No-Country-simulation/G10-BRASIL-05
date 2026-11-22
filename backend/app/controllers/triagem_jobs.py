"""Rotas para enfileirar uploads e consultar cada trabalho de triagem."""

import uuid

from fastapi import Depends, HTTPException, Request, status
from rq.exceptions import NoSuchJobError
from rq.job import Job
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.config.logger import logger
from app.config.settings import settings
from app.agent.graph import obter_estado_triagem
from app.models.triagem import DocumentoTriagemModel, UsuarioSistemaModel
from app.repositories.database import DatabaseRepository, get_db
from app.repositories.storage import StoragePersistenceError, StorageRepository
from app.schemas.triagem import EnfileirarTextoTriagemRequest
from app.services.autenticacao import exigir_usuario_atual
from app.services.document_parser import DocumentParserService
from app.services.redis_service import adquirir_lock_upload_lote, liberar_lock_upload_lote
from app.services.triagem_eventos import publicar_evento_triagem
from app.services.triagem_queue import (
    chave_proprietario_documento,
    enfileirar_documento,
    enfileirar_texto,
    liberar_reserva,
    obter_lote_triagem,
    obter_redis_fila,
    registrar_lote_triagem,
    reservar_trabalho,
)


def enfileirar_texto_triagem(
    requisicao: EnfileirarTextoTriagemRequest,
    usuario: UsuarioSistemaModel = Depends(exigir_usuario_atual),
    db: Session = Depends(get_db),
):
    """Enfileira texto colado para exibir as etapas intermediárias na interface."""
    documento_id = requisicao.documento_id or f"DOC-TX-{uuid.uuid4().hex[:10].upper()}"
    if DatabaseRepository(db).buscar_por_documento_id(documento_id):
        raise HTTPException(status_code=409, detail="Já existe uma triagem com esse identificador.")
    db.rollback()

    try:
        reserva = reservar_trabalho(usuario.id, documento_id)
    except Exception as erro:
        logger.exception("Falha de conexão com Redis ao reservar vaga para %s", documento_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de fila temporariamente indisponível.",
        ) from erro

    if reserva <= 0:
        mensagem = (
            "Já existe um trabalho com esse identificador."
            if reserva < 0
            else "Limite de 10 documentos aguardando ou em processamento por usuário."
        )
        raise HTTPException(status_code=409 if reserva < 0 else 429, detail=mensagem)

    caminho_local_txt = None
    caminho_objeto_txt = None
    try:
        storage_repo = StorageRepository()
        resultado_txt = storage_repo.salvar_arquivo_original(
            documento_id=documento_id,
            conteudo=requisicao.documento_texto.encode("utf-8"),
            nome_original=f"{documento_id}.txt",
            extensao=".txt",
            mimetype="text/plain",
            subpasta="texto",
        )
        caminho_local_txt = resultado_txt.get("caminho_local")
        caminho_objeto_txt = resultado_txt.get("caminho_objeto_fonte")
    except Exception as erro_txt:
        logger.warning("Falha ao salvar arquivo TXT no bucket para %s: %s", documento_id, erro_txt)

    try:
        job = enfileirar_texto(
            documento_id=documento_id,
            documento_texto=requisicao.documento_texto,
            tipo_arquivo=requisicao.tipo_arquivo,
            canal_origem=requisicao.canal_origem,
            usuario_id=usuario.id,
            caminho_arquivo=caminho_local_txt,
            caminho_objeto_fonte=caminho_objeto_txt,
        )
        if not job or not getattr(job, "id", None):
            raise RuntimeError("Trabalho não aceito pelo RQ.")

        lote_id = f"LOTE-TX-{uuid.uuid4().hex[:10].upper()}"
        trabalho = {"arquivo": "Texto colado", "documento_id": documento_id, "status": "na_fila"}
        try:
            registrar_lote_triagem(lote_id, usuario.id, [trabalho])
        except Exception:
            logger.warning("Falha ao registrar metadados do lote %s no Redis", lote_id)

        publicar_evento_triagem(
            usuario.id,
            "status_update",
            {
                "documento_id": documento_id,
                "lote_id": lote_id,
                "status": "na_fila",
                "arquivo": "Texto colado",
            },
        )
    except Exception:
        liberar_reserva(usuario.id, documento_id)
        logger.exception("Falha ao enfileirar texto de triagem %s", documento_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível colocar o texto na fila.",
        )

    return {
        "lote_id": lote_id,
        "documento_id": documento_id,
        "status": "na_fila",
        "trabalhos": [trabalho],
    }


async def enfileirar_upload_triagem(
    request: Request,
    usuario: UsuarioSistemaModel = Depends(exigir_usuario_atual),
    db: Session = Depends(get_db),
):
    # Trava de cooldown / idempotencia de 30 segundos por usuario
    if not adquirir_lock_upload_lote(usuario.id, ttl_segundos=30):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Um lote de documentos já foi enviado recentemente. Por favor, aguarde 30 segundos antes de enviar um novo lote.",
        )

    try:
        form = await request.form()
        # FormData.getlist preserva arquivos repetidos sob a mesma chave (padrão do Postman).
        uploads = [
            item
            for campo in ("file", "files")
            for item in form.getlist(campo)
            if isinstance(item, UploadFile)
        ]
        canal_origem = form.get("canal_origem") or "Interno"
        documento_id = form.get("documento_id")
        if not uploads:
            liberar_lock_upload_lote(usuario.id)
            raise HTTPException(status_code=400, detail="Envie um ou mais arquivos para iniciar a triagem.")
        if documento_id and len(uploads) > 1:
            liberar_lock_upload_lote(usuario.id)
            raise HTTPException(status_code=400, detail="documento_id só pode ser informado ao enviar um arquivo.")

        # Valida cada arquivo separadamente para que um inválido não descarte o lote inteiro.
        validados = []
        resultados = []
        for upload in uploads:
            conteudo = await upload.read()
            try:
                extensao = DocumentParserService.validar_arquivo(upload, conteudo)
                validados.append((upload, conteudo, extensao))
                resultados.append(None)
            except HTTPException as erro:
                validados.append(None)
                detalhe = erro.detail if isinstance(erro.detail, str) else "O arquivo não passou pela validação."
                resultados.append({
                    "arquivo": upload.filename,
                    "documento_id": None,
                    "status": "falhou",
                    "erro_codigo": "ARQUIVO_INVALIDO",
                    "erro": detalhe,
                })

        for indice, dados_arquivo in enumerate(validados):
            if dados_arquivo is None:
                continue
            upload, conteudo, extensao = dados_arquivo
            doc_id = documento_id or f"DOC-UP-{uuid.uuid4().hex[:8].upper()}"
            if DatabaseRepository(db).buscar_por_documento_id(doc_id):
                resultados[indice] = {"arquivo": upload.filename, "documento_id": doc_id, "status": "falhou", "erro_codigo": "ID_DUPLICADO", "erro": "Já existe uma triagem com esse identificador."}
                db.rollback()
                continue
            db.rollback()

            try:
                reserva = reservar_trabalho(usuario.id, doc_id)
            except Exception as erro:
                logger.exception("Falha ao reservar vaga na fila para %s", doc_id)
                resultados[indice] = {
                    "arquivo": upload.filename,
                    "documento_id": doc_id,
                    "status": "falhou",
                    "erro_codigo": "FILA_INDISPONIVEL",
                    "erro": "Serviço de fila temporariamente indisponível.",
                }
                continue

            if reserva <= 0:
                erro = (
                    "Já existe um trabalho com esse identificador."
                    if reserva < 0
                    else "Limite de 10 documentos aguardando ou em processamento por usuário."
                )
                resultados[indice] = {"arquivo": upload.filename, "documento_id": doc_id, "status": "falhou", "erro_codigo": "LIMITE_FILA" if reserva == 0 else "ID_DUPLICADO", "erro": erro}
                continue

            storage_repo = StorageRepository()
            info_storage = None
            try:
                info_storage = storage_repo.salvar_arquivo_original(
                    documento_id=doc_id,
                    conteudo=conteudo,
                    nome_original=upload.filename,
                    extensao=extensao,
                    mimetype=upload.content_type,
                )
                job = enfileirar_documento(
                    documento_id=doc_id,
                    caminho_arquivo=info_storage["caminho_local"],
                    caminho_objeto_fonte=info_storage["caminho_objeto_fonte"],
                    nome_arquivo=f"{doc_id}{extensao}",
                    extensao=extensao,
                    canal_origem=canal_origem or "Interno",
                    usuario_id=usuario.id,
                )
                if not job or not getattr(job, "id", None):
                    raise RuntimeError("Trabalho não aceito pelo RQ.")

                resultados[indice] = {"arquivo": upload.filename, "documento_id": doc_id, "status": "na_fila"}
                logger.info("Upload enfileirado: documento_id=%s, usuario_id=%s", doc_id, usuario.id)
            except Exception as erro:
                try:
                    liberar_reserva(usuario.id, doc_id)
                except Exception:
                    pass
                if info_storage:
                    storage_repo.rollback_tentativa(
                        caminho_fonte=info_storage.get("caminho_local"),
                        objetos_oci=[info_storage.get("caminho_objeto_fonte")],
                    )
                logger.exception("Falha ao enfileirar documento %s", doc_id)
                mensagem = (
                    "Não foi possível salvar o documento; a triagem não foi iniciada."
                    if isinstance(erro, StoragePersistenceError)
                    else "Não foi possível colocar o documento na fila."
                )
                resultados[indice] = {
                    "arquivo": upload.filename,
                    "documento_id": doc_id,
                    "status": "falhou",
                    "erro_codigo": "FALHA_PERSISTENCIA" if isinstance(erro, StoragePersistenceError) else "FALHA_ENFILEIRAMENTO",
                    "erro": mensagem,
                }

        # Se nenhum documento do lote foi aceito/enfileirado com sucesso, libera a trava para reenvio
        enfileirou_com_sucesso = any(
            isinstance(trabalho, dict) and trabalho.get("status") == "na_fila"
            for trabalho in resultados
        )
        if not enfileirou_com_sucesso:
            liberar_lock_upload_lote(usuario.id)

        lote_id = f"LOTE-UP-{uuid.uuid4().hex[:10].upper()}"
        try:
            registrar_lote_triagem(lote_id, usuario.id, resultados)
        except Exception:
            logger.warning("Falha ao registrar lote %s no Redis", lote_id)
        for trabalho in resultados:
            if not trabalho.get("documento_id"):
                continue
            status_trabalho = trabalho.get("status")
            publicar_evento_triagem(
                usuario.id,
                "falha" if status_trabalho == "falhou" else "status_update",
                {
                    "documento_id": trabalho["documento_id"],
                    "lote_id": lote_id,
                    "status": status_trabalho,
                    "arquivo": trabalho.get("arquivo"),
                    **(
                        {
                            "erro_codigo": trabalho.get("erro_codigo"),
                            "erro_mensagem": trabalho.get("erro"),
                        }
                        if status_trabalho == "falhou"
                        else {}
                    ),
                },
            )

        # Mantém os campos antigos para um arquivo; todos os envios também recebem o ID do lote.
        if len(resultados) == 1 and resultados[0]["status"] == "na_fila":
            return {
                "lote_id": lote_id,
                "documento_id": resultados[0]["documento_id"],
                "status": "na_fila",
                "trabalhos": resultados,
            }
        return {"lote_id": lote_id, "trabalhos": resultados}
    except HTTPException:
        raise
    except Exception:
        liberar_lock_upload_lote(usuario.id)
        raise


def _resultado_persistido(documento: DocumentoTriagemModel) -> dict:
    return {
        "status": documento.status_processamento,
        "documento_id": documento.documento_id,
        "tipo_arquivo": documento.tipo_arquivo,
        "texto_extraido": documento.documento_texto,
        "metadados_documento": documento.metadados_documento,
        "campos_rotulados": documento.campos_rotulados,
        "escopo": documento.escopo_documento,
        "legibilidade": documento.legibilidade_documento,
        "evidencias_escopo": documento.evidencias_escopo,
        "justificativa_escopo": documento.justificativa_escopo,
        "persistido": True,
        "triagem_iniciada": True,
        "classificacao": {
            "tipo_documento": documento.tipo_documento or "Não classificado",
            "especialidade": documento.especialidade or "Clínica Geral",
            "nivel_prioridade": documento.nivel_prioridade or "Rotina",
            "score_confianca_classificacao": documento.score_confianca or 0.0,
        },
        "dados_extraidos": documento.dados_extraidos or {},
        "decisao_roteamento": {
            "destino_principal": documento.destino_principal or "Auditoria_Humana",
            "requer_auditoria_humana": bool(documento.requer_auditoria_humana),
            "justificativa_roteamento": documento.justificativa_roteamento or "Processamento concluído.",
            "notificacao_gerada": None,
        },
        "armazenamento_oci": {
            "bucket": documento.bucket_oci or settings.OCI_BUCKET_NAME,
            "caminho_objeto": documento.caminho_objeto_oci or "",
        },
        "evidencias_campos": documento.evidencias_campos,
        "motivo_revisao": documento.motivo_revisao,
    }


def _resultado_identificacao_publico(identificacao: dict) -> dict:
    """Remove IDs internos e expõe somente os dados necessários à devolutiva intermediária."""
    saida = {}
    for chave, rotulo in (("paciente", "Paciente"), ("medico_solicitante", "Médico solicitante")):
        dados = identificacao.get(chave) or {}
        cadastro = dados.get("cadastro") or {}
        saida[rotulo] = {
            "status": dados.get("status", "dados_insuficientes"),
            "dados_documento": dados.get("dados_documento") or {},
            "cadastro": cadastro,
            "candidatos": dados.get("candidatos"),
        }
    return saida


def consultar_trabalho_triagem(
    documento_id: str,
    usuario: UsuarioSistemaModel = Depends(exigir_usuario_atual),
    db: Session = Depends(get_db),
):
    redis = obter_redis_fila()
    lote = obter_lote_triagem(documento_id)
    if lote is not None:
        if lote["usuario_id"] != usuario.id and usuario.papel != "ADMIN_GERAL":
            raise HTTPException(status_code=404, detail="Lote de triagem não encontrado.")

        trabalhos_lote = []
        for trabalho in lote["trabalhos"]:
            item = dict(trabalho)
            if item.get("status") == "na_fila":
                estado_item = _consultar_status_documento(item["documento_id"], db, redis)
                item.update(estado_item)
                item["arquivo"] = trabalho.get("arquivo")
            trabalhos_lote.append(item)

        estados = [item.get("status") for item in trabalhos_lote]
        finais = {"concluido", "falhou"}
        if estados and all(estado in finais for estado in estados):
            status_lote = "concluido" if all(estado == "concluido" for estado in estados) else "concluido_com_falhas"
        elif estados and all(estado == "na_fila" for estado in estados):
            status_lote = "na_fila"
        else:
            status_lote = "processando"

        return {
            "lote_id": documento_id,
            "status": status_lote,
            "total": len(trabalhos_lote),
            "concluidos": sum(estado == "concluido" for estado in estados),
            "falhas": sum(estado == "falhou" for estado in estados),
            "trabalhos": trabalhos_lote,
        }

    return _consultar_status_documento(documento_id, db, redis, usuario)


def _consultar_status_documento(
    documento_id: str,
    db: Session,
    redis,
    usuario: UsuarioSistemaModel | None = None,
) -> dict:
    proprietario = redis.get(chave_proprietario_documento(documento_id))
    if proprietario is None:
        return {"documento_id": documento_id, "status": "falhou", "erro": "Trabalho expirado ou não encontrado."}
    if usuario and int(proprietario) != usuario.id and usuario.papel != "ADMIN_GERAL":
        raise HTTPException(status_code=404, detail="Trabalho de triagem não encontrado.")

    try:
        job = Job.fetch(documento_id, connection=redis)
        estado_job = job.get_status(refresh=True)
        estado = getattr(estado_job, "value", estado_job)
    except NoSuchJobError:
        job = None
        estado = "finished"

    if estado == "finished":
        documento = DatabaseRepository(db).buscar_por_documento_id(documento_id)
        if documento is not None:
            return {
                "documento_id": documento_id,
                "status": "concluido",
                "resultado": _resultado_persistido(documento),
            }
        estado = "started"

    if estado == "failed":
        return {
            "documento_id": documento_id,
            "status": "falhou",
            "erro_codigo": (job.meta.get("erro_codigo") if job else None) or "FALHA_PROCESSAMENTO",
            "erro": (job.meta.get("erro_mensagem") if job else None)
            or "Falha no processamento. Consulte os logs do worker com este documento_id para ver a causa técnica.",
        }

    resposta = {
        "documento_id": documento_id,
        "status": "processando" if estado == "started" else "na_fila",
    }
    if estado == "started" and job is not None:
        etapa_atual = job.meta.get("etapa_atual")
        if etapa_atual:
            resposta["etapa_atual"] = etapa_atual
        if etapa_atual == "analise_clinica":
            try:
                estado_grafo = obter_estado_triagem(documento_id) or {}
                identificacao = estado_grafo.get("identificacao_cadastral")
                if identificacao:
                    resposta["resultado_parcial"] = _resultado_identificacao_publico(
                        identificacao
                    )
            except Exception:
                logger.debug(
                    "Checkpoint da identificação ainda não disponível para o trabalho %s",
                    documento_id,
                    exc_info=True,
                )
    return resposta
