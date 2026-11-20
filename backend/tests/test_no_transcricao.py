import base64
import importlib.util
from pathlib import Path

import pytest

from app.agent.graph import construir_grafo_triagem
from app.agent.nodes.transcricao import criar_node_transcricao
from app.agent.prompts import transcricao as prompt_transcricao
from app.services.document_parser import DocumentParserService

PASTA_AMOSTRAS = Path(__file__).resolve().parents[2] / "data" / "samples" / "escaneados"

_spec = importlib.util.spec_from_file_location("gerar_amostras", PASTA_AMOSTRAS / "gerar_amostras.py")
_gerador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gerador)

AMOSTRAS = {
    "receita_escaneada.png": ("\n".join(_gerador.RECEITA_ESCANEADA), "RECEITA"),
    "laudo_escaneado.pdf": ("\n".join(_gerador.LAUDO_ESCANEADO), "LAUDO"),
}

ESTADO_COM_IMAGEM = {
    "documento_texto": "",
    "imagens_documento": [{"mime_type": "image/png", "dados_base64": "aW1hZ2Vt"}],
    "requer_ocr": True,
    "erros": [],
}


def _cliente_visao_fixo(resposta: str):
    chamadas = []

    def cliente(instrucao, imagens):
        chamadas.append((instrucao, imagens))
        return resposta

    cliente.chamadas = chamadas
    return cliente


def _cliente_visao_com_erro(instrucao, imagens):
    raise RuntimeError("timeout simulado do provedor multimodal")


def test_documento_com_texto_nao_passa_pelo_ocr():
    cliente = _cliente_visao_fixo("não deveria ser chamado")
    estado = {"documento_texto": "Receita: uso oral", "requer_ocr": False}

    resultado = criar_node_transcricao(cliente)(estado)

    assert resultado == estado
    assert cliente.chamadas == []


def test_transcreve_imagem_com_modelo_multimodal():
    cliente = _cliente_visao_fixo("  Receita\nAmoxicilina 500mg  ")

    resultado = criar_node_transcricao(cliente)(ESTADO_COM_IMAGEM)

    assert resultado["documento_texto"] == "Receita\nAmoxicilina 500mg"
    assert resultado["requer_ocr"] is False
    assert resultado["transcricao"] == {"metodo": "ocr_multimodal", "versao_prompt": prompt_transcricao.VERSAO}
    instrucao, imagens = cliente.chamadas[0]
    assert instrucao == prompt_transcricao.PROMPT_TRANSCRICAO
    assert imagens == ESTADO_COM_IMAGEM["imagens_documento"]


@pytest.mark.parametrize(
    "cliente, erro_esperado",
    [
        (None, "OCR indisponível: nenhum modelo multimodal configurado."),
        (_cliente_visao_com_erro, "Falha na transcrição do documento escaneado."),
        (_cliente_visao_fixo(prompt_transcricao.RESPOSTA_SEM_TEXTO), "Documento escaneado sem texto legível."),
        (_cliente_visao_fixo("   "), "Documento escaneado sem texto legível."),
    ],
)
def test_falha_no_ocr_mantem_documento_sem_texto_e_registra_erro(cliente, erro_esperado):
    resultado = criar_node_transcricao(cliente)(ESTADO_COM_IMAGEM)

    assert resultado["documento_texto"] == ""
    assert resultado["requer_ocr"] is True
    assert erro_esperado in resultado["erros"]


def test_prompt_de_transcricao_proibe_completar_trechos_ilegiveis():
    assert prompt_transcricao.MARCADOR_ILEGIVEL in prompt_transcricao.PROMPT_TRANSCRICAO
    assert "Não complete palavras" in prompt_transcricao.PROMPT_TRANSCRICAO


@pytest.mark.parametrize("nome_arquivo", AMOSTRAS.keys())
def test_documentos_escaneados_sao_processados_pelo_grafo(nome_arquivo):
    transcricao_esperada, tipo_esperado = AMOSTRAS[nome_arquivo]
    conteudo = (PASTA_AMOSTRAS / nome_arquivo).read_bytes()
    documento = DocumentParserService.preparar_documento(conteudo, Path(nome_arquivo).suffix, nome_arquivo)
    cliente = _cliente_visao_fixo(transcricao_esperada)
    grafo = construir_grafo_triagem(transcricao=criar_node_transcricao(cliente))

    resultado = grafo.invoke(
        {
            "documento_id": nome_arquivo,
            "tipo_arquivo": documento.formato.value,
            "canal_origem": "Ambulatorio",
            "documento_texto": documento.texto,
            "imagens_documento": [imagem.model_dump() for imagem in documento.imagens],
        }
    )

    _, imagens_enviadas = cliente.chamadas[0]
    assert base64.b64decode(imagens_enviadas[0]["dados_base64"])
    assert resultado["transcricao"]["metodo"] == "ocr_multimodal"
    assert resultado["tipo_documento"] == tipo_esperado
    assert resultado["paciente"]["nome"]
    assert resultado["medico_solicitante"]["crm_uf"]
    assert resultado["status"] == "roteado"


def test_documento_escaneado_sem_ocr_vai_para_auditoria_humana():
    conteudo = (PASTA_AMOSTRAS / "receita_escaneada.png").read_bytes()
    documento = DocumentParserService.preparar_documento(conteudo, ".png", "receita_escaneada.png")
    grafo = construir_grafo_triagem(transcricao=criar_node_transcricao(None))

    resultado = grafo.invoke(
        {
            "documento_id": "SEM-OCR",
            "tipo_arquivo": documento.formato.value,
            "documento_texto": documento.texto,
            "imagens_documento": [imagem.model_dump() for imagem in documento.imagens],
        }
    )

    assert "OCR indisponível: nenhum modelo multimodal configurado." in resultado["erros"]
    assert resultado["destino_principal"] == "Auditoria_Humana"
