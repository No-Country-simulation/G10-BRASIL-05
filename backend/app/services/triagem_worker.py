"""Execução de um documento isolado por trabalho da fila Redis."""

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
from app.services.metadados_inspecao import extrair_campos_rotulados
from app.services.triagem import TriagemService
from app.services.triagem_queue import chave_trabalhos_usuario, obter_redis_fila


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


def _registrar_etapa(etapa: str) -> None:
    try:
        job = get_current_job()
        if job is not None:
            job.meta["etapa_atual"] = etapa
            job.save_meta()
    except Exception:
        logger.exception("Não foi possível atualizar a etapa do trabalho da triagem.")


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
        _registrar_etapa("leitura_documento")
        # O RQ executa jobs em processos filhos; descarta qualquer pool herdado do worker.
        engine.dispose(close=False)
        if caminho_arquivo:
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
            metadados_documento = {}
        if not texto.strip():
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
                        on_etapa=_registrar_etapa,
                    )
            finally:
                configurar_checkpointer(None)

        # O resultado clínico permanece no Postgres; o Redis guarda só fila e estado.
        logger.info(
            "Triagem em fila concluída: documento_id=%s, status=%s",
            documento_id,
            resposta.status,
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
        logger.exception("Falha no trabalho de triagem do documento %s", documento_id)
        _remover_fonte_com_falha(documento_id, caminho_arquivo, caminho_objeto_fonte)
        raise
    finally:
        redis.srem(chave_trabalhos_usuario(usuario_id), documento_id)
