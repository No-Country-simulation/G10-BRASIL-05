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
        f"/webhook/evolution?token={settings.EVOLUTION_WEBHOOK_SECRET}",
        json=payload,
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
        f"/webhook/evolution?token={settings.EVOLUTION_WEBHOOK_SECRET}",
        json=payload,
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
            f"/webhook/evolution?token={settings.EVOLUTION_WEBHOOK_SECRET}",
            json=payload,
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
        f"/webhook/evolution?token={settings.EVOLUTION_WEBHOOK_SECRET}",
        json=payload,
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
        f"/webhook/evolution?token={settings.EVOLUTION_WEBHOOK_SECRET}",
        json=payload,
    )
    assert r1.status_code == 200

    # Segunda chamada imediata com o mesmo ID: deve ignorar por idempotência
    r2 = client.post(
        f"/webhook/evolution?token={settings.EVOLUTION_WEBHOOK_SECRET}",
        json=payload,
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
