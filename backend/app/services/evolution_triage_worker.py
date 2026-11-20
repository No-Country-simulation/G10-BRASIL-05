from typing import Any, Dict

from app.config.logger import logger
from app.agent.graph import excluir_checkpoint_triagem
from app.agent.harness import (
    avaliar_escopo,
    mensagem_para_escopo,
    priorizar_revisao_medica_ilegivel,
)
from app.repositories.database import SessionLocal
from app.repositories.storage import StorageRepository
from app.schemas.triagem import RequisicaoTriagem
from app.services.document_parser import DocumentParserService
from app.services.evolution_service import EvolutionService
from app.services.triagem import TriagemService


async def worker_processar_triagem_whatsapp(dados: Dict[str, Any], doc_id: str):
    """Worker assíncrono executado em background para processar mídia e devolver triagem."""
    evolution = EvolutionService()
    numero = dados.get("numero")
    destinatario = dados.get("numero") or dados.get("remote_jid")

    try:
        # 1. Envia confirmação imediata de recebimento no chat
        msg_recebido = EvolutionService.formatar_mensagem_recebido(doc_id)
        await evolution.enviar_resposta(destinatario, msg_recebido)

        # 2. Baixa o arquivo binário (via base64 direto ou pela Evolution API)
        conteudo = await evolution.baixar_midia_bytes(
            message_id=dados["message_id"],
            base64_direto=dados.get("base64"),
        )

        if not conteudo:
            logger.error(f"Falha ao obter mídia da mensagem {dados['message_id']} ({doc_id})")
            msg_erro = EvolutionService.formatar_mensagem_erro("Não foi possível recuperar a mídia enviada.")
            await evolution.enviar_resposta(destinatario, msg_erro)
            return

        # 3. Validação do arquivo e extração de texto clínico
        extensao = DocumentParserService.validar_bytes(
            conteudo=conteudo,
            nome_arquivo=dados.get("filename") or "documento_clinico",
            content_type=dados.get("mimetype"),
        )

        texto_extraido, tipo_arquivo, avaliacao_visual = DocumentParserService.inspecionar_arquivo(
            conteudo=conteudo,
            extensao=extensao,
            nome_arquivo=dados.get("filename") or "documento_clinico",
        )

        avaliacao_escopo = priorizar_revisao_medica_ilegivel(
            avaliacao_visual or avaliar_escopo(texto_extraido)
        )
        if avaliacao_escopo.escopo in {"nao_medico", "incerto"}:
            await evolution.enviar_resposta(
                destinatario,
                EvolutionService.formatar_mensagem_erro(
                    mensagem_para_escopo(avaliacao_escopo.escopo)
                ),
            )
            return

        # Se houver legenda enviada pelo usuário, anexa ao texto clínico
        legenda = dados.get("legenda")
        if legenda:
            texto_extraido = f"{texto_extraido}\n\n[Observação/Mensagem do Usuário]: {legenda}"

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
        db = None
        try:
            db = SessionLocal()
            service = TriagemService(db)
            requisicao = RequisicaoTriagem(
                documento_id=doc_id,
                tipo_arquivo=tipo_arquivo,
                canal_origem="WhatsApp",
                documento_texto=texto_extraido,
                whatsapp_numero=numero,
                whatsapp_nome=dados.get("push_name"),
                whatsapp_message_id=dados.get("message_id"),
            )
            resposta_triagem = service.processar_triagem(
                requisicao,
                referencia_fonte=info_storage.get("caminho_local"),
                avaliacao_escopo=avaliacao_escopo.model_dump(mode="json"),
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
        finally:
            if db is not None:
                db.close()

        # 5. Formatação da Devolutiva e Envio ao Paciente/Médico no WhatsApp
        msg_devolutiva = EvolutionService.formatar_devolutiva_triagem(resposta_triagem)
        await evolution.enviar_resposta(destinatario, msg_devolutiva)
        logger.info(f"Triagem clínica {doc_id} concluída e entregue via WhatsApp para {destinatario}.")

    except Exception as exc:
        logger.exception(f"Erro inesperado no worker de WhatsApp para documento {doc_id}: {exc}")
        detalhe = getattr(exc, "detail", str(exc))
        msg_falha = EvolutionService.formatar_mensagem_erro(str(detalhe))
        await evolution.enviar_resposta(destinatario, msg_falha)
