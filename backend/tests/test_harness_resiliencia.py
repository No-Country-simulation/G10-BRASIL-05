import json
import pytest
from app.agent.harness import (
    _normalizar_trecho,
    _validar_evidencias,
    normalizar_inspecao_visual,
    priorizar_revisao_medica_ilegivel,
)
from app.schemas.escopo_documento import EvidenciaEscopo, ResultadoEscopoDocumento


def test_normalizar_trecho_remove_pontuacao():
    texto = "Hospital Santa Lúcia - Laudo... Tomografia: Pulmonar?!"
    normalizado = _normalizar_trecho(texto)
    assert "-" not in normalizado
    assert "." not in normalizado
    assert "?" not in normalizado
    assert "hospital santa lúcia laudo tomografia pulmonar" in normalizado


def test_validar_evidencias_aceita_citacao_com_diferenca_de_pontuacao():
    texto_fonte = "Hospital Santa Lúcia. Paciente com tosse crônica e dor torácica. Prescrito amoxicilina."
    resultado = ResultadoEscopoDocumento(
        escopo="medico",
        legibilidade="legivel",
        evidencias=[
            EvidenciaEscopo(
                fonte="texto",
                categoria="conteudo_clinico",
                citacao="Hospital Santa Lúcia - Paciente com tosse crônica...",
                observacao="Identificação hospitalar e sintomas",
            )
        ],
        justificativa="Documento hospitalar",
    )
    validado = _validar_evidencias(resultado, texto_fonte, permitir_evidencia_visual=False)
    assert validado.escopo == "medico"
    assert len(validado.evidencias) >= 1


def test_validar_evidencias_aceita_60_porcento_palavras_relevantes():
    texto_fonte = "Encaminhamento para cardiologia. Paciente relata palpitações e dispneia aos esforços."
    resultado = ResultadoEscopoDocumento(
        escopo="medico",
        legibilidade="legivel",
        evidencias=[
            EvidenciaEscopo(
                fonte="texto",
                categoria="conteudo_clinico",
                citacao="Paciente relata palpitações intensas e dispneia severa aos esforços frequentes",
                observacao="Sintomas relatados",
            )
        ],
        justificativa="Encaminhamento médico",
    )
    validado = _validar_evidencias(resultado, texto_fonte, permitir_evidencia_visual=False)
    assert validado.escopo == "medico"
    assert len(validado.evidencias) >= 1


def test_validar_evidencias_nunca_rebaixa_com_termo_clinico_evidente():
    texto_fonte = "CRM 123456-SP. Paciente em acompanhamento ambulatorial para exame de rotina."
    resultado = ResultadoEscopoDocumento(
        escopo="medico",
        legibilidade="legivel",
        evidencias=[
            EvidenciaEscopo(
                fonte="texto",
                categoria="conteudo_clinico",
                citacao="Citação que não existe no texto original",
                observacao="Observação sem correspondência direta",
            )
        ],
        justificativa="Análise preliminar",
    )
    validado = _validar_evidencias(resultado, texto_fonte, permitir_evidencia_visual=False)
    assert validado.escopo == "medico"
    assert len(validado.evidencias) >= 1
    assert any("crm" in (e.citacao or "").lower() or "paciente" in (e.citacao or "").lower() or "exame" in (e.citacao or "").lower() for e in validado.evidencias)


def test_normalizar_inspecao_visual_nao_zera_texto_medico_ilegivel():
    resposta_ia = json.dumps({
        "escopo": "medico",
        "legibilidade": "ilegivel",
        "transcricao": "Dr. Carlos... prescrição... 50mg",
        "evidencias": [
            {
                "fonte": "visual",
                "categoria": "estrutura_medica",
                "observacao": "Receituário com carimbo e cabeçalho médico ilegível",
            }
        ],
        "justificativa": "Receita médica manuscrita com caligrafia ilegível",
    })
    texto, resultado = normalizar_inspecao_visual(resposta_ia)
    assert resultado.escopo == "medico"
    assert resultado.legibilidade == "ilegivel"
    assert "Dr. Carlos" in texto


def test_normalizar_inspecao_visual_preenche_marcador_se_transcricao_vazia():
    resposta_ia = json.dumps({
        "escopo": "medico",
        "legibilidade": "ilegivel",
        "transcricao": "",
        "evidencias": [
            {
                "fonte": "visual",
                "categoria": "estrutura_medica",
                "observacao": "Estrutura médica sem texto legível",
            }
        ],
        "justificativa": "Documento médico ilegível",
    })
    texto, resultado = normalizar_inspecao_visual(resposta_ia)
    assert resultado.escopo == "medico"
    assert resultado.legibilidade == "ilegivel"
    assert texto == "[DOCUMENTO MÉDICO COM CALIGRAFIA ILEGÍVEL OU BAIXA NITIDEZ - ENCAMINHADO PARA AUDITORIA HUMANA]"


def test_priorizar_revisao_medica_ilegivel_define_justificativa_padrao():
    resultado = ResultadoEscopoDocumento(
        escopo="medico",
        legibilidade="ilegivel",
        evidencias=[
            EvidenciaEscopo(
                fonte="visual",
                categoria="estrutura_medica",
                observacao="Estrutura de atestado médico",
            )
        ],
        justificativa="Atestado com caligrafia difícil",
    )
    atualizado = priorizar_revisao_medica_ilegivel(resultado)
    assert atualizado.justificativa == "Documento médico com caligrafia ilegível — requer transcrição por auditor humano"


def test_desempacotamento_json_no_worker():
    payload_json = json.dumps({
        "documento_id": "DOC-TEST-123",
        "documento_texto": "HOSPITAL SANTA LUCIA - LAUDO DE TOMOGRAFIA",
        "canal_origem": "Telemedicina",
    })
    texto = payload_json
    canal_origem = "Interno"

    texto_limpo = (texto or "").strip()
    if texto_limpo.startswith("{"):
        try:
            dados_json = json.loads(texto_limpo)
            if isinstance(dados_json, dict) and "documento_texto" in dados_json:
                texto = str(dados_json["documento_texto"])
                if dados_json.get("canal_origem"):
                    canal_origem = str(dados_json["canal_origem"])
        except Exception:
            pass

    assert texto == "HOSPITAL SANTA LUCIA - LAUDO DE TOMOGRAFIA"
    assert canal_origem == "Telemedicina"

