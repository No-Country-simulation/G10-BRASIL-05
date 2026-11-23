"""Execução de um documento isolado por trabalho da fila Redis."""

import json
from pathlib import Path
import re

from fastapi import HTTPException
from langgraph.checkpoint.postgres import PostgresSaver
from rq import get_current_job

from app.agent.harness import avaliar_escopo, mensagem_para_escopo, priorizar_revisao_medica_ilegivel
from app.agent.graph import configurar_checkpointer
from app.config.logger import logger
from app.config.settings import settings
from app.errors import DependencyUnavailableError
from app.repositories.database import SessionLocal, engine
from app.repositories.storage import StorageRepository
from app.schemas.triagem import RequisicaoTriagem
from app.services.document_parser import DocumentParserService
from app.services.metadados_inspecao import extrair_campos_rotulados, extrair_metadados_documento
from app.services.triagem import TriagemService
from app.services.triagem_queue import chave_trabalhos_usuario, obter_redis_fila
from app.services.triagem_eventos import publicar_evento_triagem


def _remover_fonte_com_falha(documento_id: str, caminho: str | None, objeto: str | None) -> None:
    if not caminho and not objeto:
        return
    try:
        StorageRepository().rollback_tentativa(
            caminho_fonte=caminho,
            objetos_oci=[objeto],
        )
    except Exception:
        logger.exception("Falha ao remover fonte de trabalho não processado: %s", documento_id)


def _registrar_etapa(etapa: str, documento_id: str, usuario_id: int) -> None:
    try:
        job = get_current_job()
        if job is not None:
            job.meta["etapa_atual"] = etapa
            job.save_meta()
    except Exception:
        logger.exception("Não foi possível atualizar a etapa do trabalho da triagem.")
    if etapa == "analise_clinica":
        try:
            from app.agent.graph import obter_estado_triagem

            estado = obter_estado_triagem(documento_id) or {}
            identificacao = estado.get("identificacao_documento") or {}
            paciente = identificacao.get("paciente") or {}
            if paciente.get("nome") or paciente.get("cpf"):
                publicar_evento_triagem(
                    usuario_id,
                    "paciente_identificado",
                    {
                        "documento_id": documento_id,
                        "status": "processando",
                        "paciente_nome": paciente.get("nome"),
                        "paciente_cpf": paciente.get("cpf"),
                    },
                )
        except Exception:
            logger.exception("Não foi possível publicar a identificação parcial do documento %s", documento_id)
    publicar_evento_triagem(
        usuario_id,
        "status_update",
        {"documento_id": documento_id, "status": "processando", "etapa_atual": etapa},
    )


def _registrar_erro_publico(documento_id: str, codigo: str, mensagem: str) -> None:
    """Salva a causa legível no job para a consulta de status do documento/lote."""
    try:
        job = get_current_job()
        if job is not None:
            job.meta["erro_codigo"] = codigo
            job.meta["erro_mensagem"] = mensagem
            job.meta["documento_id"] = documento_id
            job.save_meta()
    except Exception:
        logger.exception("Não foi possível salvar a mensagem de erro do job %s", documento_id)


def _mensagem_tecnica_segura(erro: Exception, documento_id: str) -> str:
    detalhe = str(erro).replace("\n", " ").strip() or "sem detalhe fornecido pelo serviço"
    detalhe = re.sub(
        r"(?i)(api[_ -]?key|token|password|secret)\s*[:=]\s*[^\s,;]+",
        r"\1=[REDACTED]",
        detalhe,
    )
    detalhe = re.sub(r"(?i)Bearer\s+[^\s,;]+", "Bearer [REDACTED]", detalhe)
    detalhe = re.sub(
        r"(?i)(postgres(?:ql)?://[^:/\s]+:)[^@/\s]+@",
        r"\1[REDACTED]@",
        detalhe,
    )
    return f"Falha técnica ({type(erro).__name__}): {detalhe[:400]} Protocolo: {documento_id}."


def processar_documento_enfileirado(
    documento_id: str,
    caminho_arquivo: str | None,
    caminho_objeto_fonte: str | None,
    nome_arquivo: str,
    extensao: str,
    canal_origem: str,
    usuario_id: int,
    texto_documento: str | None = None,
) -> None:
    """Lê arquivo ou texto enfileirado e processa somente o documento deste job."""
    redis = obter_redis_fila()
    try:
        _registrar_etapa("leitura_documento", documento_id, usuario_id)
        # O RQ executa jobs em processos filhos; descarta qualquer pool herdado do worker.
        engine.dispose(close=False)
        if caminho_arquivo and extensao.lower() in {".txt", ".text"}:
            texto = texto_documento or ""
            if not texto and Path(caminho_arquivo).exists():
                texto = Path(caminho_arquivo).read_text(encoding="utf-8", errors="replace")
            tipo_arquivo = "texto"
            avaliacao_visual = None
            metadados_documento = extrair_metadados_documento(texto).model_dump(mode="json") if texto else {}
        elif caminho_arquivo:
            conteudo = Path(caminho_arquivo).read_bytes()
            texto, tipo_arquivo, avaliacao_visual, metadados_documento = (
                DocumentParserService.inspecionar_arquivo_com_metadados(
                    conteudo, extensao, nome_arquivo
                )
            )
        else:
            texto = texto_documento or ""
            tipo_arquivo = extensao
            avaliacao_visual = None
            metadados_documento = extrair_metadados_documento(texto).model_dump(mode="json") if texto else {}

        texto_limpo = (texto or "").strip()
        if texto_limpo.startswith("{"):
            try:
                dados_json = json.loads(texto_limpo, strict=False)
                if isinstance(dados_json, dict) and "documento_texto" in dados_json:
                    texto = str(dados_json["documento_texto"])
                    if dados_json.get("canal_origem"):
                        canal_origem = str(dados_json["canal_origem"])
                    metadados_documento = extrair_metadados_documento(texto).model_dump(mode="json") if texto else {}
            except Exception:
                pass

            if texto == texto_limpo and '"documento_texto"' in texto_limpo:
                import re
                match_texto = re.search(r'"documento_texto"\s*:\s*"((?:[^"\\]|\\.)*)"', texto_limpo, re.DOTALL)
                if match_texto:
                    try:
                        texto = match_texto.group(1).encode("utf-8").decode("unicode_escape").strip()
                    except Exception:
                        texto = match_texto.group(1).strip()
                    match_canal = re.search(r'"canal_origem"\s*:\s*"([^"]+)"', texto_limpo)
                    if match_canal:
                        canal_origem = match_canal.group(1).strip()
                    metadados_documento = extrair_metadados_documento(texto).model_dump(mode="json") if texto else {}

        eh_medico_ou_ilegivel = False
        if avaliacao_visual:
            if avaliacao_visual.escopo == "medico" or avaliacao_visual.legibilidade == "ilegivel":
                eh_medico_ou_ilegivel = True

        if not texto.strip():
            if eh_medico_ou_ilegivel:
                texto = "[DOCUMENTO MÉDICO COM CALIGRAFIA ILEGÍVEL OU BAIXA NITIDEZ - ENCAMINHADO PARA AUDITORIA HUMANA]"
            else:
                raise HTTPException(status_code=422, detail="O documento está vazio.")
        campos_rotulados = extrair_campos_rotulados(texto)
        avaliacao = priorizar_revisao_medica_ilegivel(
            avaliacao_visual or avaliar_escopo(texto)
        )
        if avaliacao.escopo in {"nao_medico", "incerto"}:
            raise HTTPException(
                status_code=422,
                detail=mensagem_para_escopo(avaliacao.escopo),
                headers={"X-Error-Code": "DOCUMENTO_FORA_ESCOPO" if avaliacao.escopo == "nao_medico" else "ESCOPO_NAO_CONFIRMADO"},
            )

        requisicao = RequisicaoTriagem(
            documento_id=documento_id,
            tipo_arquivo=tipo_arquivo,
            canal_origem=canal_origem,
            documento_texto=texto,
        )

        with PostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
            checkpointer.setup()
            configurar_checkpointer(checkpointer)
            try:
                with SessionLocal() as db:
                    resposta = TriagemService(db).processar_triagem(
                        requisicao,
                        referencia_fonte=caminho_arquivo,
                        avaliacao_escopo=avaliacao.model_dump(mode="json"),
                        metadados_documento=metadados_documento,
                        campos_rotulados=campos_rotulados,
                        on_etapa=lambda etapa: _registrar_etapa(etapa, documento_id, usuario_id),
                    )
            finally:
                configurar_checkpointer(None)

        # O estado operacional permanece no Postgres; o payload clínico/auditável
        # segue para o Mongo por meio do outbox transacional.
        logger.info(
            "Triagem em fila concluída: documento_id=%s, status=%s",
            documento_id,
            resposta.status,
        )
        publicar_evento_triagem(
            usuario_id,
            "concluido",
            {"documento_id": documento_id, "status": "concluido"},
        )
    except HTTPException as erro:
        mensagem = erro.detail if isinstance(erro.detail, str) else "O documento não pôde ser processado."
        if erro.status_code == 422:
            codigo = (erro.headers or {}).get("X-Error-Code", "DOCUMENTO_NAO_PROCESSAVEL")
        elif erro.status_code in {502, 503}:
            codigo = (erro.headers or {}).get("X-Error-Code", "SERVICO_ANALISE_INDISPONIVEL")
        else:
            codigo = "ERRO_ARQUIVO"
        _registrar_erro_publico(documento_id, codigo, mensagem)
        publicar_evento_triagem(
            usuario_id,
            "falha",
            {
                "documento_id": documento_id,
                "status": "falhou",
                "erro_codigo": codigo,
                "erro_mensagem": mensagem,
            },
        )
        logger.exception("Triagem em fila recusada ou interrompida: %s", documento_id)
        _remover_fonte_com_falha(documento_id, caminho_arquivo, caminho_objeto_fonte)
        raise
    except Exception as erro:
        if isinstance(erro, DependencyUnavailableError):
            codigo_erro = "SERVICO_INDISPONIVEL"
            mensagem_erro = str(erro)
        else:
            codigo_erro = "FALHA_TECNICA_PROCESSAMENTO"
            mensagem_erro = _mensagem_tecnica_segura(erro, documento_id)
        _registrar_erro_publico(documento_id, codigo_erro, mensagem_erro)
        publicar_evento_triagem(
            usuario_id,
            "falha",
            {
                "documento_id": documento_id,
                "status": "falhou",
                "erro_codigo": codigo_erro,
                "erro_mensagem": "Falha técnica durante o processamento.",
            },
        )
        logger.exception("Falha no trabalho de triagem do documento %s", documento_id)
        _remover_fonte_com_falha(documento_id, caminho_arquivo, caminho_objeto_fonte)
        raise
    finally:
        redis.srem(chave_trabalhos_usuario(usuario_id), documento_id)
