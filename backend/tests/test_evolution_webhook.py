import base64
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config.settings import settings
from app.services.evolution_service import EvolutionService
from app.schemas.triagem import (
    RespostaTriagem,
    ClassificacaoDocumento,
    DadosExtraidos,
    Paciente,
    MedicoSolicitante,
    DecisaoRoteamento,
    ArmazenamentoOCI,
    NotificacaoAlerta,
)

client = TestClient(app)


def test_status_webhook_evolution():
    """Testa endpoint GET /webhook/evolution informando metadados de conectividade."""
    response = client.get("/webhook/evolution")
    assert response.status_code == 200
    dados = response.json()
    assert dados["status"] == "online"
    assert dados["provedor"] == "Evolution API (WhatsApp)"
    assert "instancia_configurada" in dados


def test_webhook_autenticacao_invalida():
    """Verifica rejeição HTTP 401 quando o secret configurado não é atendido."""
    payload = {"event": "messages.upsert"}
    # Envia sem token ou token incorreto
    response = client.post(
        "/webhook/evolution?token=token_invalido_123",
        json=payload,
    )
    assert response.status_code == 401
    corpo = response.json()
    msg = corpo.get("erro", {}).get("mensagem") or corpo.get("detail", "")
    assert "inválido" in msg.lower() or "não autorizado" in msg.lower()


def test_webhook_ignora_mensagem_do_proprio_bot():
    """Valida que mensagens do próprio bot (fromMe=True) são ignoradas com status 200."""
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511999998888@s.whatsapp.net",
                "fromMe": True,
                "id": "MSG-FROM-ME-01",
            },
            "message": {"conversation": "Mensagem enviada pelo bot"},
        },
    }
    response = client.post(
        "/webhook/evolution",
        json=payload,
        headers={"x-webhook-token": settings.EVOLUTION_WEBHOOK_SECRET},
    )
    assert response.status_code == 200
    dados = response.json()
    assert dados["status"] == "ignored"


def test_webhook_ignora_grupo_ou_broadcast():
    """Valida que mensagens de grupos (@g.us) são ignoradas."""
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "120363024829384920@g.us",
                "fromMe": False,
                "id": "MSG-GRUPO-01",
            },
            "message": {"conversation": "Mensagem de grupo"},
        },
    }
    response = client.post(
        "/webhook/evolution",
        json=payload,
        headers={"x-webhook-token": settings.EVOLUTION_WEBHOOK_SECRET},
    )
    assert response.status_code == 200
    dados = response.json()
    assert dados["status"] == "ignored"


def test_webhook_mensagem_texto_responde_ajuda():
    """Valida recebimento de mensagem de texto com enfileiramento de resposta de ajuda."""
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511999991111@s.whatsapp.net",
                "fromMe": False,
                "id": f"MSG-TXT-HELP-{uuid.uuid4().hex[:8]}",
            },
            "pushName": "Paciente Teste",
            "message": {"conversation": "Olá, como funciona a triagem?"},
        },
    }
    with patch.object(EvolutionService, "enviar_resposta", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        response = client.post(
            "/webhook/evolution",
            json=payload,
            headers={"x-webhook-token": settings.EVOLUTION_WEBHOOK_SECRET},
        )
        assert response.status_code == 200
        dados = response.json()
        assert dados["status"] == "replied_info"
        assert dados["numero"] == "5511999991111"


def test_webhook_mensagem_midia_enfileira_triagem():
    """Valida recebimento de mídia (imagem/documento) e enfileiramento da triagem."""
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511988887777@s.whatsapp.net",
                "fromMe": False,
                "id": f"MSG-MEDIA-{uuid.uuid4().hex[:8]}",
            },
            "pushName": "Dr. Fernando",
            "messageType": "imageMessage",
            "message": {
                "imageMessage": {
                    "mimetype": "image/jpeg",
                    "caption": "Paciente com dispneia aguda",
                    "base64": base64.b64encode(b"fake-image-bytes").decode("utf-8"),
                }
            },
        },
    }
    response = client.post(
        "/webhook/evolution",
        json=payload,
        headers={"x-webhook-token": settings.EVOLUTION_WEBHOOK_SECRET},
    )
    assert response.status_code == 200
    dados = response.json()
    assert dados["status"] == "queued"
    assert "DOC-WPP-" in dados["documento_id"]
    assert dados["numero"] == "5511988887777"


def test_webhook_idempotencia_duplicada():
    """Valida que mensagens com o mesmo ID são ignoradas na segunda chamada."""
    msg_id = "MSG-IDEMPOTENCIA-999"
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511977776666@s.whatsapp.net",
                "fromMe": False,
                "id": msg_id,
            },
            "message": {"conversation": "teste idempotência"},
        },
    }
    # Primeira chamada: deve processar
    r1 = client.post(
        "/webhook/evolution",
        json=payload,
        headers={"x-webhook-token": settings.EVOLUTION_WEBHOOK_SECRET},
    )
    assert r1.status_code == 200

    # Segunda chamada imediata com o mesmo ID: deve ignorar por idempotência
    r2 = client.post(
        "/webhook/evolution",
        json=payload,
        headers={"x-webhook-token": settings.EVOLUTION_WEBHOOK_SECRET},
    )
    assert r2.status_code == 200
    dados2 = r2.json()
    assert dados2["status"] == "ignored"
    assert dados2["motivo"] == "já_processado"


def test_formatacao_devolutiva_triagem():
    """Valida a formatação humanizada de WhatsApp a partir de um RespostaTriagem."""
    resposta = RespostaTriagem(
        status="processado",
        documento_id="DOC-TEST-123",
        classificacao=ClassificacaoDocumento(
            tipo_documento="Laudo Tomográfico",
            especialidade="Pneumologia",
            nivel_prioridade="Urgente",
            score_confianca_classificacao=0.98,
        ),
        dados_extraidos=DadosExtraidos(
            paciente=Paciente(nome="Maria de Lurdes", idade=64),
            medico_solicitante=MedicoSolicitante(nome="Dr. Marcos Alves", crm="12345-SP"),
            exame_realizado="Tomografia de Tórax",
            diagnostico_principal="Pneumonia Bacteriana",
            cid_sugerido="J18.9",
        ),
        decisao_roteamento=DecisaoRoteamento(
            destino_principal="UTI_Semi_Intensiva",
            requer_auditoria_humana=False,
            justificativa_roteamento="Sinais evidentes de consolidação alveolar.",
            notificacao_gerada=NotificacaoAlerta(
                canal="Alerta_Plantao",
                mensagem="Atenção: Paciente idosa com comprometimento pulmonar.",
            ),
        ),
        armazenamento_oci=ArmazenamentoOCI(
            bucket="mediflow-bucket",
            caminho_objeto="processados/DOC-TEST-123.json",
            status_backup="sucesso",
        ),
    )

    texto_formatado = EvolutionService.formatar_devolutiva_triagem(resposta)
    assert "RESULTADO DA TRIAGEM CLÍNICA" in texto_formatado
    assert "DOC-TEST-123" in texto_formatado
    assert "Maria de Lurdes" in texto_formatado
    assert "Dr. Marcos Alves" in texto_formatado
    assert "🔴 *URGENTE*" in texto_formatado
    assert "98%" in texto_formatado
    assert "UTI Semi Intensiva" in texto_formatado
    assert "Alerta:" in texto_formatado


def test_endpoint_antigo_de_login_institucional_removido():
    """O login institucional agora é servido exclusivamente pelo endpoint central."""
    response = client.post(
        "/webhook/evolution/autenticar-institucional",
        json={"email": "mediflow@equipe.com.br", "senha": "senha-qualquer"},
    )
    assert response.status_code == 404


def test_endpoints_gestao_instancia_exigem_jwt_institucional():
    """O cabeçalho de identidade legado não concede acesso à gestão da instância."""
    sem_identidade = client.get("/webhook/evolution/status-instancia")
    assert sem_identidade.status_code in (401, 403)
    identidade_legada = client.get(
        "/webhook/evolution/status-instancia",
        headers={"x-usuario-email": "mediflow@equipe.com.br"},
    )
    assert identidade_legada.status_code in (401, 403)


def test_webhook_texto_consulta_protocolo_no_banco():
    """Valida que o agente autônomo responde com o status real do protocolo quando consultado por texto."""
    from app.models.triagem import DocumentoTriagemModel
    from app.repositories.database import DatabaseRepository, SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        repo = DatabaseRepository(db)
        doc_id = f"DOC-WPP-{uuid.uuid4().hex[:8].upper()}"
        repo.salvar(
            DocumentoTriagemModel(
                documento_id=doc_id,
                tipo_arquivo="PDF",
                canal_origem="WhatsApp",
                tipo_documento="Laudo Laboratorial",
                especialidade="Hematologia",
                nivel_prioridade="Rotina",
                score_confianca=0.95,
                destino_principal="Ambulatorio_Geral",
                requer_auditoria_humana=False,
                status_processamento="processado",
                dados_extraidos={
                    "paciente": {"nome": "CarlosConsulta", "idade": 41},
                    "medico_solicitante": {"nome": "Dra. Silvia", "crm": "54321-SP"},
                    "exame_realizado": "Hemograma Completo",
                    "diagnostico_principal": "Exame dentro da normalidade",
                    "cid_sugerido": "Z00.0",
                },
                whatsapp_numero="5511999993333",
                whatsapp_nome="Carlos Consulta",
            )
        )
        db.commit()
    finally:
        db.close()

    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511999993333@s.whatsapp.net",
                "fromMe": False,
                "id": f"MSG-PROTO-{uuid.uuid4().hex[:8]}",
            },
            "pushName": "Carlos Consulta",
            "message": {"conversation": f"Olá, quero saber o resultado do protocolo {doc_id}"},
        },
    }
    with patch.object(EvolutionService, "enviar_resposta", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        response = client.post(
            "/webhook/evolution",
            json=payload,
            headers={"x-webhook-token": settings.EVOLUTION_WEBHOOK_SECRET},
        )
        assert response.status_code == 200
        dados = response.json()
        assert dados["status"] == "replied_info"
        assert dados["protocolo_consultado"] == doc_id
        texto_enviado = mock_send.call_args[0][1]
        assert doc_id in texto_enviado
        assert "CarlosConsulta" in texto_enviado
        assert "Hemograma Completo" in texto_enviado


def test_retencao_diagnostico_em_revisao_humana_e_notificacao_pos_auditoria():
    """Garante que documentos em revisão humana não expõem diagnóstico/CID antes da decisão e notificam após auditoria."""
    resposta_pendente = RespostaTriagem(
        status="em_auditoria",
        documento_id="DOC-WPP-AUDIT01",
        classificacao=ClassificacaoDocumento(
            tipo_documento="Receituário Médico",
            especialidade="Clínica Geral",
            nivel_prioridade="Rotina",
            score_confianca_classificacao=0.55,
        ),
        dados_extraidos=DadosExtraidos(
            paciente=Paciente(nome="Joana Pendente", idade=33),
            medico_solicitante=MedicoSolicitante(nome="Dr. Teste", crm="99999-SP"),
            exame_realizado="Consulta",
            diagnostico_principal="DIAGNOSTICO_NAO_VALIDADO_SECRETO",
            cid_sugerido="R69",
        ),
        decisao_roteamento=DecisaoRoteamento(
            destino_principal="Auditoria_Humana",
            requer_auditoria_humana=True,
            justificativa_roteamento="Baixa legibilidade no carimbo médico.",
        ),
        armazenamento_oci=ArmazenamentoOCI(
            bucket="mediflow-bucket",
            caminho_objeto="auditoria/DOC-WPP-AUDIT01.json",
            status_backup="sucesso",
        ),
        motivo_revisao="Baixa legibilidade no carimbo médico.",
    )

    msg_retida = EvolutionService.formatar_devolutiva_triagem(resposta_pendente)
    assert "DOCUMENTO EM REVISÃO HUMANA" in msg_retida
    assert "DOC-WPP-AUDIT01" in msg_retida
    assert "DIAGNOSTICO_NAO_VALIDADO_SECRETO" not in msg_retida
    assert "R69" not in msg_retida

    class _DocFicticio:
        documento_id = "DOC-WPP-AUDIT01"
        status_processamento = "aguardando_reenvio"
        requer_auditoria_humana = False
        justificativa_roteamento = "Foto desfocada."

    msg_reenvio = EvolutionService.formatar_notificacao_pos_auditoria(
        _DocFicticio(),
        status_aprovacao="solicitar_reenvio",
        justificativa="Foto desfocada, envie nova imagem nítida.",
    )
    assert "ATUALIZAÇÃO DO PROTOCOLO DOC-WPP-AUDIT01" in msg_reenvio
    assert "Foto desfocada" in msg_reenvio


def test_decisao_auditoria_dispara_notificacao_ativa_no_whatsapp():
    """Valida que registrar_decisao_medica envia mensagem automática ao WhatsApp do remetente."""
    from types import SimpleNamespace
    from unittest.mock import Mock
    from app.schemas.triagem import DecisaoAuditoriaRequest
    from app.services.triagem import TriagemService

    service = TriagemService.__new__(TriagemService)
    service.db_repo = Mock()
    service.db_repo.buscar_por_documento_id.return_value = SimpleNamespace(
        documento_id="DOC-WPP-CALLBACK1",
        whatsapp_numero="5511977771234",
        caminho_fonte=None,
        caminho_objeto_oci=None,
    )
    doc_final = SimpleNamespace(
        documento_id="DOC-WPP-CALLBACK1",
        whatsapp_numero="5511977771234",
        status_processamento="aguardando_reenvio",
        requer_auditoria_humana=False,
        tipo_documento="Receituário Médico",
        especialidade="Clínica Geral",
        nivel_prioridade="Rotina",
        score_confianca=0.8,
        destino_principal="Aguardando_Reenvio",
        justificativa_roteamento="Foto ilegível.",
        dados_extraidos={},
    )
    service.db_repo.registrar_decisao.return_value = doc_final
    service.storage_repo = Mock()
    service.redis_service = Mock()
    service.nosql_repo = Mock()

    payload = DecisaoAuditoriaRequest(
        status_aprovacao="solicitar_reenvio",
        auditor_nome="Dr. Roberto Silva",
        justificativa="Imagem borrada, por favor reenvie.",
    )

    with patch(
        "app.services.triagem.retomar_agente_triagem",
        return_value={"status": "aguardando_reenvio", "justificativa_roteamento": "Imagem borrada."},
    ), patch.object(EvolutionService, "enviar_resposta_sincrona", return_value=True) as mock_sync:
        service.registrar_decisao_medica("DOC-WPP-CALLBACK1", payload)
        assert mock_sync.called
        assert mock_sync.call_args[0][0] == "5511977771234"
        assert "DOC-WPP-CALLBACK1" in mock_sync.call_args[0][1]
