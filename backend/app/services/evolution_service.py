import asyncio
import base64
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, Tuple
import httpx

from app.config.settings import settings
from app.config.logger import logger
from app.config.mensagens_whatsapp import (
    MENSAGEM_BOAS_VINDAS_TEXTO,
    mensagem_confirmacao_recebimento,
    mensagem_documento_invalido,
    formatar_mensagem_devolutiva,
)
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
        numero_puro = remote_jid.split("@")[0].split(":")[0]
        # Remove caracteres não numéricos
        return re.sub(r"\D", "", numero_puro)

    @staticmethod
    def resolver_identificador_whatsapp(remote_jid: str, push_name: Optional[str] = None) -> Tuple[str, str]:
        """Resolve o número de telefone real e o JID canônico (@s.whatsapp.net).

        Em mensagens originadas de dispositivos vinculados (WhatsApp Web/Multi-Device),
        o WhatsApp envia um LID (@lid) em vez do número de telefone.
        Esta função consulta o cache do Redis e a base da Evolution API para mapear
        o LID ao número de telefone E.164 real do contato.
        """
        if not remote_jid:
            return "", ""

        if "@lid" not in remote_jid:
            numero_limpo = EvolutionService.normalizar_numero(remote_jid)
            return numero_limpo, f"{numero_limpo}@s.whatsapp.net"

        # Trata identificador com LID
        lid_id = re.sub(r"\D", "", remote_jid.split("@")[0].split(":")[0])
        if not lid_id:
            return "", remote_jid

        # 1. Checa cache no Redis
        chave_cache = f"whatsapp:lid_to_phone:{lid_id}"
        try:
            from app.services.redis_service import RedisAuditService
            redis_cli = RedisAuditService()._client
            cached_phone = redis_cli.get(chave_cache)
            if cached_phone:
                if isinstance(cached_phone, bytes):
                    cached_phone = cached_phone.decode("utf-8")
                logger.info(f"Mapeamento LID {lid_id} -> {cached_phone} recuperado do cache Redis.")
                return str(cached_phone), f"{cached_phone}@s.whatsapp.net"
        except Exception as e:
            logger.debug(f"Falha ao ler cache Redis de LID: {e}")

        # 2. Consulta banco de dados da Evolution API (PostgreSQL compartilhado)
        telefone_encontrado = None
        try:
            from sqlalchemy import create_engine, text
            evo_url = settings.DATABASE_URL.rsplit("/", 1)[0] + "/evolution"
            engine = create_engine(evo_url, pool_pre_ping=True)
            with engine.connect() as conn:
                # Query 1: Via MessageUpdate (relaciona atualizações do LID a mensagens com número real)
                sql_updates = text(
                    """
                    SELECT m.key->>'remoteJid' as phone_jid
                    FROM "MessageUpdate" mu
                    JOIN "Message" m ON mu."messageId" = m.id
                    WHERE (mu."remoteJid" LIKE :padrao OR mu."participant" LIKE :padrao)
                      AND m.key->>'remoteJid' LIKE '%@s.whatsapp.net'
                    LIMIT 1;
                    """
                )
                res = conn.execute(sql_updates, {"padrao": f"%{lid_id}%"}).scalar()
                if res:
                    telefone_encontrado = EvolutionService.normalizar_numero(res)

                # Query 2: Via Contact (mesmo profilePicUrl entre LID e número real)
                if not telefone_encontrado:
                    sql_contacts = text(
                        """
                        SELECT c2."remoteJid"
                        FROM "Contact" c1
                        JOIN "Contact" c2 ON c1."profilePicUrl" = c2."profilePicUrl" AND c1."profilePicUrl" IS NOT NULL
                        WHERE c1."remoteJid" LIKE :padrao AND c2."remoteJid" LIKE '%@s.whatsapp.net'
                        LIMIT 1;
                        """
                    )
                    res_c = conn.execute(sql_contacts, {"padrao": f"%{lid_id}%"}).scalar()
                    if res_c:
                        telefone_encontrado = EvolutionService.normalizar_numero(res_c)

                # Query 3: Via pushName em Contact se disponível
                if not telefone_encontrado and push_name:
                    sql_push = text(
                        """
                        SELECT "remoteJid"
                        FROM "Contact"
                        WHERE "pushName" = :push_name AND "remoteJid" LIKE '%@s.whatsapp.net'
                        ORDER BY "updatedAt" DESC
                        LIMIT 1;
                        """
                    )
                    res_p = conn.execute(sql_push, {"push_name": push_name}).scalar()
                    if res_p:
                        telefone_encontrado = EvolutionService.normalizar_numero(res_p)
            engine.dispose()
        except Exception as err:
            logger.warning(f"Não foi possível consultar mapeamento de LID no banco Evolution: {err}")

        if telefone_encontrado:
            logger.info(f"LID {lid_id} mapeado com sucesso para o telefone {telefone_encontrado}")
            try:
                from app.services.redis_service import RedisAuditService
                RedisAuditService()._client.setex(chave_cache, 604800, telefone_encontrado)
            except Exception:
                pass
            return telefone_encontrado, f"{telefone_encontrado}@s.whatsapp.net"

        logger.warning(f"LID {lid_id} não pôde ser resolvido para número real. Usando fallback.")
        return lid_id, remote_jid

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

        # Resolve número de telefone canônico (lid -> phone se necessário)
        numero_resolvido, jid_resolvido = EvolutionService.resolver_identificador_whatsapp(remote_jid, push_name)

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
            extensao_imagem = ".heic" if mimetype.lower().split(";", 1)[0] in {"image/heic", "image/heif"} else ".jpg"
            filename = f"imagem_wpp_{message_id}{extensao_imagem}"
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
                "remote_jid": jid_resolvido,
                "original_remote_jid": remote_jid,
                "numero": numero_resolvido,
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
            "remote_jid": jid_resolvido,
            "original_remote_jid": remote_jid,
            "numero": numero_resolvido,
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
        # Se for um JID com @s.whatsapp.net, extrai apenas os dígitos para a Evolution
        numero_destino = numero
        if "@s.whatsapp.net" in numero or (numero and numero.replace("+", "").isdigit()):
            numero_destino = re.sub(r"\D", "", numero)

        payload = {
            "number": numero_destino,
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

    def enviar_resposta_sincrona(self, numero: str, texto: str) -> bool:
        """Ponte síncrona segura para disparo de mensagens WhatsApp a partir de fluxos síncronos (ex.: decisão de auditoria)."""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                with ThreadPoolExecutor(max_workers=1) as executor:
                    futuro = executor.submit(asyncio.run, self.enviar_resposta(numero, texto))
                    return bool(futuro.result(timeout=15.0))
            return bool(asyncio.run(self.enviar_resposta(numero, texto)))
        except Exception as e:
            logger.error(f"Falha no disparo síncrono para WhatsApp {numero}: {e}")
            return False

    # --------------------------------------------------------------------------
    # 4. Formatações Amigáveis & Agente Autônomo (WhatsApp Markdown)
    # --------------------------------------------------------------------------
    @staticmethod
    def extrair_protocolo_do_texto(texto: str) -> Optional[str]:
        """Detecta se a mensagem de texto contém um identificador de protocolo (ex.: DOC-WPP-1234ABCD)."""
        if not texto:
            return None
        match = re.search(r"\b(DOC-[A-Z0-9-]{4,})\b", texto.upper())
        return match.group(1) if match else None

    @staticmethod
    def formatar_mensagem_recebido(documento_id: str) -> str:
        return mensagem_confirmacao_recebimento(documento_id)

    @staticmethod
    def formatar_mensagem_ajuda(push_name: Optional[str] = None) -> str:
        return MENSAGEM_BOAS_VINDAS_TEXTO

    @staticmethod
    def formatar_mensagem_erro(motivo: str) -> str:
        return mensagem_documento_invalido(motivo)

    @staticmethod
    def formatar_mensagem_revisao_humana(documento_id: str, motivo: Optional[str] = None) -> str:
        """Mensagem enviada quando o documento cai em Revisão Humana (retém diagnóstico e CID não validados)."""
        detalhe = motivo or "O documento requer conferência da equipe clínica para segurança do paciente."
        return (
            f"🏥 *DOCUMENTO EM REVISÃO HUMANA - MEDIFLOW*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Protocolo:* `{documento_id}`\n"
            f"⏳ *Status:* Encaminhado para *Revisão Humana (Human-in-the-Loop)*\n\n"
            f"📋 *Observação:* {detalhe}\n\n"
            f"🔒 *Segurança Clínica:* Para sua segurança, a análise requer validação da equipe.\n"
            f"📲 Você receberá o resultado validado e o redirecionamento automaticamente por aqui "
            f"assim que a revisão for concluída."
        )

    @staticmethod
    def formatar_devolutiva_triagem(resposta: RespostaTriagem) -> str:
        """Gera devolutiva para o WhatsApp apontando o que é o documento e para onde o usuário deve seguir."""
        roteamento = resposta.decisao_roteamento
        if resposta.status == "em_auditoria" or roteamento.requer_auditoria_humana:
            motivo = resposta.motivo_revisao or roteamento.justificativa_roteamento
            return EvolutionService.formatar_mensagem_revisao_humana(
                documento_id=resposta.documento_id,
                motivo=motivo,
            )

        classif = resposta.classificacao
        dados = resposta.dados_extraidos

        paciente_nome = dados.paciente.nome if dados and dados.paciente else None
        medico_nome = dados.medico_solicitante.nome if dados and dados.medico_solicitante else None

        return formatar_mensagem_devolutiva(
            protocolo=resposta.documento_id,
            tipo_documento_raw=classif.tipo_documento,
            especialidade=classif.especialidade,
            prioridade=classif.nivel_prioridade,
            destino_raw=roteamento.destino_principal,
            paciente_nome=paciente_nome,
            medico_nome=medico_nome,
            is_urgente=classif.nivel_prioridade.upper() in ("URGENTE", "EMERGENCIA"),
        )

    @staticmethod
    def formatar_status_protocolo(doc: Any) -> str:
        """Formata o status atual de um documento consultado por protocolo no banco de dados."""
        status_proc = (getattr(doc, "status_processamento", "") or "").lower()
        requer_auditoria = bool(getattr(doc, "requer_auditoria_humana", False))

        if status_proc == "em_auditoria" or requer_auditoria:
            motivo = getattr(doc, "motivo_revisao", None) or getattr(doc, "justificativa_roteamento", None)
            return EvolutionService.formatar_mensagem_revisao_humana(doc.documento_id, motivo)

        if status_proc == "aguardando_reenvio":
            justificativa = getattr(doc, "justificativa_roteamento", None) or "A imagem ou PDF enviado está ilegível."
            return (
                f"🔄 *SOLICITAÇÃO DE REENVIO - MEDIFLOW*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *Protocolo:* `{doc.documento_id}`\n"
                f"⚠️ *Status:* Aguardando reenvio de documento legível\n\n"
                f"📋 *Avaliação da Equipe:* {justificativa}\n\n"
                f"Por favor, envie uma nova foto bem iluminada e sem cortes ou o arquivo PDF original."
            )

        if status_proc in ("auditoria_rejeitado", "rejeitado"):
            justificativa = getattr(doc, "justificativa_roteamento", None) or "Documento reprovado na revisão clínica."
            return (
                f"❌ *TRIAGEM NÃO APROVADA - MEDIFLOW*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 *Protocolo:* `{doc.documento_id}`\n"
                f"📋 *Parecer da Revisão:* {justificativa}\n\n"
                f"Caso deseje submeter um novo documento médico, basta enviá-lo em PDF ou imagem."
            )

        dados = getattr(doc, "dados_extraidos", None) or {}
        paciente_info = dados.get("paciente") or {}
        medico_info = dados.get("medico_solicitante") or {}
        prioridade = (getattr(doc, "nivel_prioridade", None) or "Rotina").upper()
        prioridade_icone = "🔴" if prioridade in ("URGENTE", "EMERGENCIA") else "🟢"
        destino = (getattr(doc, "destino_principal", None) or "Fluxo_Padrao").replace("_", " ")

        paciente_nome = paciente_info.get("nome") or "Não identificado"
        paciente_idade = f", {paciente_info.get('idade')} anos" if paciente_info.get("idade") else ""
        medico_nome = medico_info.get("nome") or "Não informado"
        medico_crm = f" (CRM: {medico_info.get('crm')})" if medico_info.get("crm") else ""
        exame = dados.get("exame_realizado") or "Exame Clínico Geral"
        diag = dados.get("diagnostico_principal") or "Avaliação clínica concluída"
        cid = dados.get("cid_sugerido") or "N/A"

        return "\n".join(
            [
                "🏥 *RESULTADO DA TRIAGEM CLÍNICA - MEDIFLOW*",
                "━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"🆔 *Protocolo:* `{doc.documento_id}`",
                f"✅ *Status:* Validado e Concluído",
                f"📋 *Classificação:* {getattr(doc, 'tipo_documento', None) or 'Documento Clínico'}",
                f"🩺 *Especialidade:* {getattr(doc, 'especialidade', None) or 'Clínica Geral'}",
                f"🚨 *Prioridade:* {prioridade_icone} *{prioridade}*",
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
                f"• Destino: *{destino}*",
                "━━━━━━━━━━━━━━━━━━━━━━━━━",
                "_Documento auditado e armazenado com segurança no MediFlow._",
            ]
        )

    @staticmethod
    def formatar_notificacao_pos_auditoria(
        doc: Any,
        status_aprovacao: str,
        justificativa: str,
    ) -> str:
        """Gera a mensagem ativa disparada ao remetente do WhatsApp após decisão na Auditoria Humana."""
        acao = (status_aprovacao or "").lower()
        status_proc = (getattr(doc, "status_processamento", "") or "").lower()

        if acao == "solicitar_reenvio" or status_proc == "aguardando_reenvio":
            return (
                f"🔄 *ATUALIZAÇÃO DO PROTOCOLO {doc.documento_id} - MEDIFLOW*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Nossa equipe concluiu a verificação do seu documento e identificou que "
                f"*a legibilidade não permite uma análise clínica segura*.\n\n"
                f"📋 *Orientação do Revisor:* {justificativa}\n\n"
                f"📸 Por favor, envie novamente uma foto nítida (sem cortes ou reflexos) ou o arquivo *PDF* original."
            )

        if acao == "rejeitado" or status_proc in ("auditoria_rejeitado", "rejeitado"):
            return (
                f"❌ *ATUALIZAÇÃO DO PROTOCOLO {doc.documento_id} - MEDIFLOW*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Após revisão humana, o documento enviado não pôde ser aprovado para o fluxo clínico.\n\n"
                f"📋 *Parecer da Auditoria:* {justificativa}\n\n"
                f"Se necessário, envie um novo documento médico atualizado em formato PDF ou Imagem."
            )

        return EvolutionService.formatar_status_protocolo(doc)

    @staticmethod
    def responder_mensagem_texto_autonomo(
        texto: str,
        push_name: str = "Paciente",
        db_repo: Optional[Any] = None,
    ) -> str:
        """Processa mensagens de texto do WhatsApp orientando o envio de arquivo ou consultando protocolo."""
        texto_limpo = (texto or "").strip()
        protocolo = EvolutionService.extrair_protocolo_do_texto(texto_limpo)

        if protocolo and db_repo is not None:
            doc = db_repo.buscar_por_documento_id(protocolo)
            if doc:
                return EvolutionService.formatar_status_protocolo(doc)

        return MENSAGEM_BOAS_VINDAS_TEXTO

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
        tentativas = 5
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                for tentativa in range(tentativas):
                    resp = await client.get(url, headers=self.headers)
                    if resp.status_code != 200:
                        logger.warning(
                            "Evolution falhou ao gerar QR Code.",
                            extra={"status_code": resp.status_code, "path": "/instance/connect"},
                        )
                        return {"sucesso": False, "erro": resp.text, "status_code": resp.status_code}

                    dados = resp.json()
                    b64 = dados.get("base64") if isinstance(dados, dict) else None
                    if b64:
                        return {
                            "sucesso": True,
                            "base64": b64,
                            "code": dados.get("code"),
                            "count": dados.get("count", 0),
                            "dados": dados,
                        }

                    if tentativa < tentativas - 1:
                        await asyncio.sleep(1)

                logger.warning(
                    "Evolution respondeu sem imagem de QR Code após novas tentativas.",
                    extra={"status_code": 200, "path": "/instance/connect"},
                )
                return {
                    "sucesso": False,
                    "erro": "Evolution respondeu sem imagem de QR Code após 5 tentativas.",
                    "status_code": 502,
                }
        except Exception as e:
            logger.exception(
                "Erro ao consultar QR Code na Evolution.",
                extra={"path": "/instance/connect"},
            )
            return {"sucesso": False, "erro": str(e)}

    async def configurar_webhook(self, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """Configura automaticamente o webhook da instância apontando para o backend."""
        if len(settings.EVOLUTION_WEBHOOK_SECRET) < 32:
            return {
                "sucesso": False,
                "erro": "EVOLUTION_WEBHOOK_SECRET precisa ter pelo menos 32 caracteres.",
                "status_code": 503,
            }
        if not self.api_key:
            return {
                "sucesso": False,
                "erro": "EVOLUTION_API_KEY não está configurada.",
                "status_code": 503,
            }
        url = f"{self.api_url}/webhook/set/{self.instance}"
        target_url = webhook_url or settings.EVOLUTION_WEBHOOK_URL
        if not target_url:
            return {
                "sucesso": False,
                "erro": "EVOLUTION_WEBHOOK_URL não está configurada.",
                "status_code": 503,
            }
        payload = {
            "webhook": {
                "enabled": True,
                "url": target_url,
                "headers": {"x-webhook-token": settings.EVOLUTION_WEBHOOK_SECRET},
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
