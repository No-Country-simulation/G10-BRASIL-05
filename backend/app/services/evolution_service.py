import base64
import logging
import re
from typing import Optional, Dict, Any, Tuple
import httpx

from app.config.settings import settings
from app.config.logger import logger
from app.schemas.triagem import RespostaTriagem


class EvolutionService:
    """Módulo isolado de integração com a Evolution API (WhatsApp).

    Implementa:
    1. Recebimento e normalização de mensagens/eventos do webhook
    2. Download da mídia (PDF/Imagem) em base64
    3. Envio de mensagens de texto / devolutivas formatadas para o WhatsApp
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        instance: Optional[str] = None,
    ):
        self.api_url = (api_url or settings.EVOLUTION_API_URL).rstrip("/")
        self.api_key = api_key or settings.EVOLUTION_API_KEY
        self.instance = instance or settings.EVOLUTION_INSTANCE_NAME

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    # --------------------------------------------------------------------------
    # 1. Extração e Normalização de Mensagem
    # --------------------------------------------------------------------------
    @staticmethod
    def normalizar_numero(remote_jid: str) -> str:
        """Extrai apenas os dígitos do remetente (remove @s.whatsapp.net ou sufixos)."""
        numero_puro = remote_jid.split("@")[0]
        # Remove caracteres não numéricos
        return re.sub(r"\D", "", numero_puro)

    @staticmethod
    def extrair_dados_mensagem(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extrai os dados clínicos e de roteamento da mensagem recebida via webhook Evolution.

        Retorna None se a mensagem não contiver dados válidos ou se for 'fromMe'.
        """
        data = payload.get("data") or payload
        key = data.get("key") or {}

        from_me = bool(key.get("fromMe", False))
        if from_me:
            logger.info("Mensagem enviada pelo próprio bot (fromMe=True). Ignorando.")
            return None

        remote_jid = key.get("remoteJid") or ""
        # Ignora mensagens de grupos (@g.us) e canais de broadcast se for o caso
        if "@g.us" in remote_jid or "status@broadcast" in remote_jid:
            logger.info(f"Mensagem de grupo ou broadcast ignorada: {remote_jid}")
            return None

        message_id = key.get("id") or ""
        push_name = data.get("pushName") or "Paciente"
        message_obj = data.get("message") or {}

        # Desempacota invólucros comuns do WhatsApp/Baileys (ex: viewOnce, ephemeral, caption wrappers)
        for wrapper in ["ephemeralMessage", "viewOnceMessage", "viewOnceMessageV2", "documentWithCaptionMessage"]:
            if wrapper in message_obj and isinstance(message_obj[wrapper], dict):
                inner = message_obj[wrapper].get("message") or message_obj[wrapper]
                if isinstance(inner, dict):
                    message_obj = {**message_obj, **inner}

        # Identifica tipo de mensagem e mídia
        message_type = data.get("messageType") or ""
        image_data = message_obj.get("imageMessage")
        doc_data = message_obj.get("documentMessage")

        midia_base64 = (
            (image_data or {}).get("base64")
            or (doc_data or {}).get("base64")
            or data.get("base64")
            or payload.get("base64")
            or message_obj.get("base64")
        )
        mimetype = None
        filename = None
        legenda = ""

        if image_data:
            message_type = "imageMessage"
            mimetype = image_data.get("mimetype") or "image/jpeg"
            filename = f"imagem_wpp_{message_id}.jpg"
            legenda = image_data.get("caption") or ""
        elif doc_data:
            message_type = "documentMessage"
            mimetype = doc_data.get("mimetype") or "application/pdf"
            filename = doc_data.get("fileName") or f"doc_wpp_{message_id}.pdf"
            legenda = doc_data.get("caption") or ""
        else:
            # Mensagem de texto simples ou conversa
            texto_conversa = (
                message_obj.get("conversation")
                or (message_obj.get("extendedTextMessage") or {}).get("text")
                or ""
            )
            return {
                "message_id": message_id,
                "remote_jid": remote_jid,
                "numero": EvolutionService.normalizar_numero(remote_jid),
                "push_name": push_name,
                "message_type": message_type or "conversation",
                "tipo": "texto",
                "texto": texto_conversa,
                "mimetype": None,
                "filename": None,
                "base64": None,
            }

        return {
            "message_id": message_id,
            "remote_jid": remote_jid,
            "numero": EvolutionService.normalizar_numero(remote_jid),
            "push_name": push_name,
            "message_type": message_type,
            "tipo": "midia",
            "mimetype": mimetype,
            "filename": filename,
            "legenda": legenda,
            "base64": midia_base64,
        }

    # --------------------------------------------------------------------------
    # 2. Download / Obtenção de Mídia
    # --------------------------------------------------------------------------
    async def baixar_midia_bytes(
        self,
        message_id: str,
        base64_direto: Optional[str] = None,
    ) -> Optional[bytes]:
        """Obtém os bytes do arquivo a partir de base64 embutido ou chamando a Evolution API."""
        raw_b64 = base64_direto

        if not raw_b64:
            # Consulta endpoint da Evolution API v2 para obter a mídia em base64
            url = f"{self.api_url}/chat/getBase64FromMediaMessage/{self.instance}"
            payload = {
                "message": {
                    "key": {
                        "id": message_id,
                    }
                },
                "convertToMp4": False,
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, json=payload, headers=self.headers)
                    if resp.status_code == 200:
                        dados = resp.json()
                        raw_b64 = dados.get("base64")
                    else:
                        logger.error(
                            f"Erro ao baixar mídia da Evolution API (status {resp.status_code}): {resp.text}"
                        )
                        return None
            except Exception as e:
                logger.error(f"Falha na conexão HTTP com Evolution API: {e}")
                return None

        if not raw_b64:
            return None

        # Limpa possível prefixo data:image/...;base64,
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]

        try:
            return base64.b64decode(raw_b64)
        except Exception as e:
            logger.error(f"Falha ao decodificar base64 da mensagem {message_id}: {e}")
            return None

    # --------------------------------------------------------------------------
    # 3. Envio de Mensagens de Resposta
    # --------------------------------------------------------------------------
    async def enviar_resposta(self, numero: str, texto: str) -> bool:
        """Envia mensagem de texto via endpoint /message/sendText da Evolution API."""
        url = f"{self.api_url}/message/sendText/{self.instance}"
        payload = {
            "number": numero,
            "text": texto,
            "delay": 1200,
            "linkPreview": False,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                if resp.status_code in (200, 201):
                    logger.info(f"Mensagem enviada com sucesso para WhatsApp {numero}")
                    return True
                else:
                    logger.error(
                        f"Falha ao enviar resposta para {numero} (status {resp.status_code}): {resp.text}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Exceção ao chamar /message/sendText para {numero}: {e}")
            return False

    # --------------------------------------------------------------------------
    # 4. Formatações Amigáveis (WhatsApp Markdown)
    # --------------------------------------------------------------------------
    @staticmethod
    def formatar_mensagem_recebido(documento_id: str) -> str:
        return (
            f"🏥 *MediFlow - Triagem Clínica*\n\n"
            f"Recebi seu documento com sucesso!\n"
            f"🆔 *Protocolo:* `{documento_id}`\n\n"
            f"⏳ *Analisando conteúdo clínico...* Em instantes enviaremos a avaliação."
        )

    @staticmethod
    def formatar_mensagem_ajuda() -> str:
        return (
            f"🏥 *Olá! Sou o assistente de triagem clínica do MediFlow.*\n\n"
            f"Para realizar uma triagem automatizada, por favor me envie um laudo, "
            f"receita ou documento médico em formato *PDF* ou *Foto/Imagem* (PNG, JPG).\n\n"
            f"Assim que enviado, nossa inteligência clínica analisará e devolverá o resultado aqui mesmo."
        )

    @staticmethod
    def formatar_mensagem_erro(motivo: str) -> str:
        return (
            f"⚠️ *Não foi possível concluir a análise do seu documento.*\n\n"
            f"*Motivo:* {motivo}\n\n"
            f"Por favor, certifique-se de enviar uma imagem legível ou arquivo PDF válido (até 10 MB)."
        )

    @staticmethod
    def formatar_devolutiva_triagem(resposta: RespostaTriagem) -> str:
        """Gera devolutiva médica legível e profissional para o chat do WhatsApp."""
        classif = resposta.classificacao
        dados = resposta.dados_extraidos
        roteamento = resposta.decisao_roteamento

        prioridade_icone = "🔴" if classif.nivel_prioridade.upper() in ("URGENTE", "EMERGENCIA") else "🟢"
        confianca_pct = int(classif.score_confianca_classificacao * 100)

        paciente_nome = dados.paciente.nome or "Não identificado"
        paciente_idade = f", {dados.paciente.idade} anos" if dados.paciente.idade else ""
        medico_nome = dados.medico_solicitante.nome or "Não informado"
        medico_crm = f" (CRM: {dados.medico_solicitante.crm})" if dados.medico_solicitante.crm else ""

        exame = dados.exame_realizado or "Exame Clínico Geral"
        diag = dados.diagnostico_principal or "Avaliação clínica pendente"
        cid = dados.cid_sugerido or "N/A"

        msg = [
            "🏥 *RESULTADO DA TRIAGEM CLÍNICA - MEDIFLOW*",
            "━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🆔 *Protocolo:* `{resposta.documento_id}`",
            f"📋 *Classificação:* {classif.tipo_documento}",
            f"🩺 *Especialidade:* {classif.especialidade}",
            f"🎯 *Confiança:* {confianca_pct}%",
            f"🚨 *Prioridade:* {prioridade_icone} *{classif.nivel_prioridade.upper()}*",
            "",
            "👤 *Dados do Paciente:*",
            f"• Nome: {paciente_nome}{paciente_idade}",
            f"• Solicitante: {medico_nome}{medico_crm}",
            "",
            "🔬 *Achados Clínicos:*",
            f"• Exame: {exame}",
            f"• Diagnóstico Sugerido: {diag}",
            f"• CID Sugerido: `{cid}`",
            "",
            "🏥 *Roteamento Hospitalar:*",
            f"• Destino: *{roteamento.destino_principal.replace('_', ' ')}*",
        ]

        if roteamento.requer_auditoria_humana:
            msg.append("⚠️ *Aviso:* Este documento foi direcionado para *Auditoria Médica (Human-in-the-Loop)*.")

        if roteamento.notificacao_gerada:
            msg.append(f"🔔 *Alerta:* {roteamento.notificacao_gerada.mensagem}")

        msg.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
        msg.append("_Documento auditado e armazenado com segurança no MediFlow._")

        return "\n".join(msg)

    # --------------------------------------------------------------------------
    # 5. Gestão de Instância e Conexão (QR Code / Status)
    # --------------------------------------------------------------------------
    async def obter_estado_conexao(self) -> Dict[str, Any]:
        """Consulta o estado de conexão da instância (open, close, connecting)."""
        url = f"{self.api_url}/instance/connectionState/{self.instance}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    dados = resp.json()
                    # Normaliza estrutura da v2
                    inst = dados.get("instance") or dados
                    state = inst.get("state") or "close"
                    return {"conectado": state == "open", "estado": state, "detalhes": dados}
                elif resp.status_code == 404:
                    return {"conectado": False, "estado": "not_found", "detalhes": "Instância não criada"}
                return {"conectado": False, "estado": "erro", "detalhes": resp.text}
        except Exception as e:
            logger.warning(f"Erro ao consultar estado da instância {self.instance}: {e}")
            return {"conectado": False, "estado": "offline", "detalhes": str(e)}

    async def criar_instancia(self) -> Dict[str, Any]:
        """Cria ou reinicia a instância na Evolution API para geração de QR Code."""
        url = f"{self.api_url}/instance/create"
        payload = {
            "instanceName": self.instance,
            "token": self.api_key,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                if resp.status_code in (200, 201):
                    return {"sucesso": True, "dados": resp.json()}
                elif resp.status_code == 403:
                    # Instância já existe, tenta obter qrcode
                    return {"sucesso": True, "aviso": "Instância já existente", "dados": resp.json()}
                return {"sucesso": False, "erro": resp.text, "status_code": resp.status_code}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}

    async def obter_qrcode(self) -> Dict[str, Any]:
        """Obtém o QR Code em base64 da instância para exibição no frontend."""
        url = f"{self.api_url}/instance/connect/{self.instance}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    dados = resp.json()
                    b64 = dados.get("base64")
                    code = dados.get("code")
                    count = dados.get("count", 0)
                    return {
                        "sucesso": True,
                        "base64": b64,
                        "code": code,
                        "count": count,
                        "dados": dados,
                    }
                return {"sucesso": False, "erro": resp.text, "status_code": resp.status_code}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}

    async def configurar_webhook(self, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """Configura automaticamente o webhook da instância apontando para o backend."""
        url = f"{self.api_url}/webhook/set/{self.instance}"
        target_url = webhook_url or f"http://172.24.0.1:8000/webhook/evolution?token={settings.EVOLUTION_WEBHOOK_SECRET}"
        payload = {
            "webhook": {
                "enabled": True,
                "url": target_url,
                "byEvents": False,
                "base64": True,
                "events": ["MESSAGES_UPSERT"],
            }
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                if resp.status_code in (200, 201):
                    return {"sucesso": True, "url": target_url, "dados": resp.json()}
                return {"sucesso": False, "erro": resp.text, "status_code": resp.status_code}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}

    async def desconectar(self) -> Dict[str, Any]:
        """Desconecta a sessão atual do WhatsApp (logout)."""
        url = f"{self.api_url}/instance/logout/{self.instance}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(url, headers=self.headers)
                return {"sucesso": resp.status_code in (200, 204), "resposta": resp.text}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}
