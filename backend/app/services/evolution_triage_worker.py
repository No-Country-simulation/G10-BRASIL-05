from typing import Any, Dict

from app.config.logger import logger
from app.agent.nodes.filtro_elegibilidade import avaliar_elegibilidade
from app.repositories.database import SessionLocal
from app.repositories.storage import StorageRepository
from app.schemas.triagem import RequisicaoTriagem
from app.services.document_parser import DocumentParserService
from app.services.evolution_service import EvolutionService
from app.services.triagem import TriagemService


async def worker_processar_triagem_whatsapp(dados: Dict[str, Any], doc_id: str):
    """Worker assíncrono executado em background para processar mídia e devolver triagem."""
    evolution = EvolutionService()
    numero = dados["numero"]

    try:
        # 1. Envia confirmação imediata de recebimento no chat
        msg_recebido = EvolutionService.formatar_mensagem_recebido(doc_id)
        await evolution.enviar_resposta(numero, msg_recebido)

        # 2. Baixa o arquivo binário (via base64 direto ou pela Evolution API)
        conteudo = await evolution.baixar_midia_bytes(
            message_id=dados["message_id"],
            base64_direto=dados.get("base64"),
        )

        if not conteudo:
            logger.error(f"Falha ao obter mídia da mensagem {dados['message_id']} ({doc_id})")
            msg_erro = EvolutionService.formatar_mensagem_erro("Não foi possível recuperar a mídia enviada.")
            await evolution.enviar_resposta(numero, msg_erro)
            return

        # 3. Validação do arquivo e extração de texto clínico
        extensao = DocumentParserService.validar_bytes(
            conteudo=conteudo,
            nome_arquivo=dados.get("filename") or "documento_clinico",
            content_type=dados.get("mimetype"),
        )

        texto_extraido, tipo_arquivo = DocumentParserService.extrair_texto(
            conteudo=conteudo,
            extensao=extensao,
            nome_arquivo=dados.get("filename") or "documento_clinico",
        )

        # Se houver legenda enviada pelo usuário, anexa ao texto clínico
        legenda = dados.get("legenda")
        if legenda:
            texto_extraido = f"{texto_extraido}\n\n[Observação/Mensagem do Usuário]: {legenda}"

        elegibilidade, _, _ = avaliar_elegibilidade(texto_extraido)
        if elegibilidade == "nao_medico":
            await evolution.enviar_resposta(
                numero,
                EvolutionService.formatar_mensagem_erro(
                    "O documento enviado não é médico. O processamento foi recusado."
                ),
            )
            return

        # Salva a fonte original somente depois do filtro de escopo.
        storage_repo = StorageRepository()
        info_storage = storage_repo.salvar_arquivo_original(
            documento_id=doc_id,
            conteudo=conteudo,
            nome_original=dados.get("filename"),
            extensao=extensao,
            mimetype=dados.get("mimetype"),
        )
        logger.info(
            f"Arquivo do WhatsApp persistido na pasta Storage: '{info_storage['nome_arquivo']}' "
            f"({info_storage['tamanho_bytes']} bytes) em {info_storage['caminho_local']}"
        )

        # 4. Execução da Triagem Clínica via Agente LangGraph e Persistência
        db = SessionLocal()
        try:
            service = TriagemService(db)
            requisicao = RequisicaoTriagem(
                documento_id=doc_id,
                tipo_arquivo=tipo_arquivo,
                canal_origem="WhatsApp",
                documento_texto=texto_extraido,
            )
            resposta_triagem = service.processar_triagem(
                requisicao,
                referencia_fonte=info_storage.get("caminho_local"),
            )
        except Exception:
            storage_repo.rollback_tentativa(
                caminho_fonte=info_storage.get("caminho_local"),
                objetos_oci=[info_storage.get("caminho_objeto_fonte")],
            )
            raise
        finally:
            db.close()

        # 5. Formatação da Devolutiva e Envio ao Paciente/Médico no WhatsApp
        msg_devolutiva = EvolutionService.formatar_devolutiva_triagem(resposta_triagem)
        await evolution.enviar_resposta(numero, msg_devolutiva)
        logger.info(f"Triagem clínica {doc_id} concluída e entregue via WhatsApp para {numero}.")

    except Exception as exc:
        logger.exception(f"Erro inesperado no worker de WhatsApp para documento {doc_id}: {exc}")
        detalhe = getattr(exc, "detail", str(exc))
        msg_falha = EvolutionService.formatar_mensagem_erro(str(detalhe))
        await evolution.enviar_resposta(numero, msg_falha)
