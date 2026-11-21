from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from services import cliente_mock
from services.erros import ErroDeApi

PASTA_DAS_PAGINAS = Path(__file__).resolve().parents[1] / "pages"
TRIAGEM = "1_Triagem_Clinica.py"
AUDITORIA = "2_Auditoria_Humana.py"
HISTORICO = "3_Historico.py"
DOCUMENTO_DA_FILA = "DOC-CLIN-2026-0003"

PREFIXO = "/api/v1/triagem"
ITEM_DA_API = {
    "documento_id": "DOC-API-1",
    "tipo_documento": "Receituario Medico",
    "score_confianca": 0.6,
    "dados_extraidos": {
        "paciente": {"nome": "Joao Lima", "idade": 40},
        "medico_solicitante": {"nome": "Dr. Paulo", "crm": None},
    },
    "justificativa_roteamento": "CRM ausente.",
}
RESPOSTA_DA_TRIAGEM = {
    "status": "processado",
    "documento_id": "DOC-API-2",
    "classificacao": {
        "tipo_documento": "Laudo de Exame de Imagem",
        "especialidade": "Radiologia",
        "nivel_prioridade": "Urgente",
        "score_confianca_classificacao": 0.95,
    },
    "dados_extraidos": {"paciente": {"nome": "Carlos", "idade": 52}},
    "decisao_roteamento": {
        "destino_principal": "Fila_Emergencia_Medica",
        "requer_auditoria_humana": False,
        "justificativa_roteamento": "Achado crítico.",
        "notificacao_gerada": None,
    },
}


def _abrir(pagina: str) -> AppTest:
    return AppTest.from_file(str(PASTA_DAS_PAGINAS / pagina), default_timeout=30).run()


def _analisar_texto(at: AppTest, texto: str, canal: str = "Pronto_Socorro") -> AppTest:
    at.radio[0].set_value("Colar texto").run()
    at.text_area[0].set_value(texto)
    at.selectbox[0].select(canal)
    return at.button[0].click().run()


def _clicar(at: AppTest, rotulo: str) -> AppTest:
    return next(botao for botao in at.button if botao.label == rotulo).click().run()


def _aprovar(at: AppTest, documento_id: str) -> AppTest:
    at.selectbox[0].select(documento_id).run()
    at.text_input(key="auditor").set_value("Dra. Ana")
    return _clicar(at, "Aprovar")


def _erro_de_conexao(requisicao):
    raise httpx.ConnectError("sem conexão")


@pytest.mark.parametrize("pagina", [TRIAGEM, AUDITORIA, HISTORICO])
def test_paginas_abrem_sem_erro(pagina):
    at = _abrir(pagina)

    assert not at.exception
    assert not at.error


# ---------- Triagem (modo demonstração)

@pytest.mark.parametrize(
    "texto, trecho_esperado",
    [
        ("suspeita de TEP", "URGENTE: encaminhado para a fila de emergência médica"),
        ("receita com CRM ausente", "Revisão humana necessária"),
        ("receita de rotina", "Rotina: aprovado automaticamente"),
    ],
)
def test_triagem_por_texto_mostra_o_destino(texto, trecho_esperado):
    at = _analisar_texto(_abrir(TRIAGEM), texto)

    alertas = [e.value for e in at.warning] + [e.value for e in at.success] + [e.value for e in at.markdown]
    assert not at.exception
    assert any(trecho_esperado in alerta for alerta in alertas)


def test_triagem_pede_o_canal_de_origem():
    at = _abrir(TRIAGEM)
    at.radio[0].set_value("Colar texto").run()
    at.text_area[0].set_value("receita de rotina")

    at.button[0].click().run()

    assert at.warning[0].value == "Selecione o canal de origem do documento."


def test_triagem_mostra_a_previa_do_pdf_enviado():
    at = _abrir(TRIAGEM)

    at.file_uploader[0].set_value(("laudo.pdf", b"%PDF-1.4", "application/pdf")).run()

    assert "laudo.pdf" in at.info[0].value


def test_triagem_repassa_o_arquivo_pdf_para_o_upload(monkeypatch):
    recebidos = {}
    enviar_original = cliente_mock.enviar_documento

    def enviar_falso(requisicao, arquivo=None):
        recebidos.update(requisicao=requisicao, arquivo=arquivo)
        return enviar_original(requisicao)

    monkeypatch.setattr(cliente_mock, "enviar_documento", enviar_falso)
    at = _abrir(TRIAGEM)
    at.file_uploader[0].set_value(("laudo.pdf", b"%PDF-1.4", "application/pdf")).run()
    at.selectbox[0].select("Pronto_Socorro")

    at.button[0].click().run()

    assert not at.exception
    assert recebidos["requisicao"]["tipo_arquivo"] == "PDF"
    assert recebidos["arquivo"].name == "laudo.pdf"
    assert recebidos["arquivo"].getvalue() == b"%PDF-1.4"


def test_triagem_mostra_erro_da_api_sem_quebrar(monkeypatch):
    def falhar(requisicao, arquivo=None):
        raise ErroDeApi("A API demorou demais para responder. Tente novamente.")

    monkeypatch.setattr(cliente_mock, "enviar_documento", falhar)

    at = _analisar_texto(_abrir(TRIAGEM), "receita de rotina")

    assert not at.exception
    assert at.error[0].value == "A API demorou demais para responder. Tente novamente."


def test_triagem_em_demonstracao_mostra_onde_o_documento_foi_salvo():
    at = _analisar_texto(_abrir(TRIAGEM), "receita de rotina")

    assert any("mediflow-documentos-clinicos/processados/rotina" in s.value for s in at.success)


# ---------- Triagem (API real)

@pytest.mark.usefixtures("modo_api_real")
def test_triagem_real_mostra_o_resultado_devolvido_pela_api(simular_rotas):
    simular_rotas({("POST", PREFIXO): (200, RESPOSTA_DA_TRIAGEM)})

    at = _analisar_texto(_abrir(TRIAGEM), "suspeita de TEP")

    assert not at.exception
    assert not at.error
    assert any("DOC-API-2" in c.value for c in at.caption)


@pytest.mark.usefixtures("modo_api_real")
@pytest.mark.parametrize(
    "rota, trecho_do_erro",
    [
        ((500, {"erro": {"codigo": "ERRO_INTERNO", "mensagem": "Erro interno do servidor."}}), "Erro interno do servidor."),
        ((422, {"erro": {"codigo": "VALIDACAO", "mensagem": "Dados inválidos.", "detalhes": [{"campo": "documento_id", "motivo": "formato inválido"}]}}), "documento_id: formato inválido"),
        (_erro_de_conexao, "Não foi possível conectar à API"),
        (lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("lento")), "demorou demais"),
    ],
)
def test_triagem_real_com_falha_da_api_mostra_erro_e_nenhum_resultado(simular_rotas, rota, trecho_do_erro):
    simular_rotas({("POST", PREFIXO): rota})

    at = _analisar_texto(_abrir(TRIAGEM), "suspeita de TEP")

    assert not at.exception
    assert trecho_do_erro in at.error[0].value
    assert not at.success
    assert not any("URGENTE" in m.value for m in at.markdown)
    assert not at.caption


@pytest.mark.usefixtures("modo_api_real")
def test_triagem_real_com_backup_falho_nao_aparece_como_salvo(simular_rotas):
    resposta = {
        **RESPOSTA_DA_TRIAGEM,
        "armazenamento_oci": {"bucket": "b", "caminho_objeto": "c.json", "status_backup": "falha: OCI fora do ar"},
    }
    simular_rotas({("POST", PREFIXO): (200, resposta)})

    at = _analisar_texto(_abrir(TRIAGEM), "suspeita de TEP")

    assert not at.exception
    assert any("backup não foi gravado" in e.value for e in at.error)
    assert not any("Documento salvo" in s.value for s in at.success)


@pytest.mark.usefixtures("modo_api_real")
def test_triagem_real_envia_pdf_por_upload_multipart(simular_rotas):
    requisicoes = simular_rotas({("POST", f"{PREFIXO}/upload"): (200, RESPOSTA_DA_TRIAGEM)})
    at = _abrir(TRIAGEM)
    at.file_uploader[0].set_value(("laudo.pdf", b"%PDF-1.4", "application/pdf")).run()
    at.selectbox[0].select("Pronto_Socorro")

    at.button[0].click().run()

    assert not at.exception
    assert [r.url.path for r in requisicoes] == [f"{PREFIXO}/upload"]
    assert b'filename="laudo.pdf"' in requisicoes[0].content


# ---------- Auditoria (modo demonstração)

def test_auditoria_lista_primeiro_o_mais_urgente():
    at = _abrir(AUDITORIA)

    assert at.selectbox[0].options[0].endswith("Emergência")


def test_auditoria_sem_documentos_avisa(monkeypatch):
    monkeypatch.setattr(cliente_mock, "listar_fila_auditoria", lambda: [])

    at = _abrir(AUDITORIA)

    assert at.info[0].value == "Nenhum documento aguardando auditoria."


def test_auditoria_em_demonstracao_nao_simula_a_decisao():
    at = _aprovar(_abrir(AUDITORIA), DOCUMENTO_DA_FILA)

    assert not at.exception
    assert not at.success
    assert "Nada foi salvo nem enviado" in at.error[0].value
    assert "continua pendente" in at.error[0].value
    assert at.selectbox[0].value == DOCUMENTO_DA_FILA


def test_auditoria_exige_identificacao_do_auditor():
    at = _abrir(AUDITORIA)
    at.selectbox[0].select(DOCUMENTO_DA_FILA).run()

    at = _clicar(at, "Aprovar")

    assert at.warning[-1].value == "Informe a identificação do auditor."


# ---------- Auditoria (API real)

@pytest.fixture
def api_de_auditoria(simular_rotas, modo_api_real):
    """API com um documento pendente. A decisão tira o documento da fila apenas se for aceita."""
    estado = {"pendentes": [ITEM_DA_API], "decisoes": []}

    def registrar(requisicao):
        estado["decisoes"].append(requisicao)
        estado["pendentes"] = []
        return httpx.Response(200, json={"mensagem": "Decisão de auditoria registrada com sucesso."})

    def configurar(rota_da_decisao=registrar):
        requisicoes = simular_rotas(
            {
                ("GET", f"{PREFIXO}/auditoria"): lambda r: httpx.Response(200, json=estado["pendentes"]),
                ("POST", f"{PREFIXO}/auditoria/DOC-API-1/decisao"): rota_da_decisao,
            }
        )
        return estado, requisicoes

    return configurar


def test_auditoria_real_registra_a_decisao_e_tira_o_documento_da_fila(api_de_auditoria):
    estado, _ = api_de_auditoria()

    at = _aprovar(_abrir(AUDITORIA), "DOC-API-1")

    assert not at.exception
    assert "Decisão de auditoria registrada com sucesso." in at.success[0].value
    assert len(estado["decisoes"]) == 1
    assert at.info[0].value == "Nenhum documento aguardando auditoria."


@pytest.mark.parametrize(
    "resposta, trecho_do_erro",
    [
        (lambda r: httpx.Response(500, json={"erro": {"codigo": "ERRO_INTERNO", "mensagem": "Erro interno do servidor."}}), "Erro interno do servidor."),
        (lambda r: httpx.Response(409, json={"erro": {"codigo": "CONFLITO", "mensagem": "Documento já finalizado."}}), "Documento já finalizado."),
        (lambda r: httpx.Response(422, json={"erro": {"codigo": "VALIDACAO", "mensagem": "Dados inválidos.", "detalhes": [{"campo": "status_aprovacao", "motivo": "valor inválido"}]}}), "status_aprovacao: valor inválido"),
        (lambda r: httpx.Response(200, text="<html>erro</html>"), "resposta inválida"),
        (_erro_de_conexao, "Não foi possível conectar à API"),
        (lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("lento")), "demorou demais"),
    ],
)
def test_auditoria_real_com_falha_nao_confirma_e_mantem_o_documento_pendente(api_de_auditoria, resposta, trecho_do_erro):
    api_de_auditoria(rota_da_decisao=resposta)

    at = _aprovar(_abrir(AUDITORIA), "DOC-API-1")

    assert not at.exception
    assert not at.success
    assert trecho_do_erro in at.error[0].value
    assert "continua pendente" in at.error[0].value
    assert at.selectbox[0].value == "DOC-API-1"


def test_auditoria_real_com_api_fora_do_ar_nao_mostra_documentos_de_demonstracao(modo_api_real, simular_api):
    simular_api(_erro_de_conexao)

    at = _abrir(AUDITORIA)

    assert "Não foi possível conectar à API" in at.error[0].value
    assert not at.selectbox


# ---------- Histórico

def test_historico_filtra_por_status():
    at = _abrir(HISTORICO)

    at.radio[0].set_value("Urgência").run()

    assert at.caption[0].value == "1 documento(s)"


def test_historico_sem_documentos_no_filtro_avisa():
    at = _abrir(HISTORICO)

    at.radio[0].set_value("Rejeitado").run()

    assert at.info[0].value == "Nenhum documento encontrado para este filtro."


def test_historico_mostra_o_detalhe_do_documento():
    at = _abrir(HISTORICO)

    at.selectbox[0].select("DOC-CLIN-2026-8942").run()

    assert not at.exception
    assert at.subheader[0].value == "Documento DOC-CLIN-2026-8942"


@pytest.mark.usefixtures("modo_api_real")
def test_historico_real_lista_os_documentos_da_api(simular_rotas):
    documento = {"documento_id": "DOC-API-9", "destino_principal": "Fluxo_Padrao", "created_at": "2026-11-04T10:00:00"}
    simular_rotas({("GET", f"{PREFIXO}/documentos"): (200, [documento])})

    at = _abrir(HISTORICO)

    assert not at.exception
    assert list(at.dataframe[0].value["Documento"]) == ["DOC-API-9"]


@pytest.mark.usefixtures("modo_api_real")
def test_historico_real_com_api_fora_do_ar_mostra_erro_e_nao_os_dados_de_demonstracao(simular_api):
    simular_api(_erro_de_conexao)

    at = _abrir(HISTORICO)

    assert "Não foi possível conectar à API" in at.error[0].value
    assert not at.dataframe


@pytest.mark.usefixtures("modo_api_real")
def test_historico_real_informa_que_o_detalhe_nao_existe_no_backend(simular_rotas):
    documento = {"documento_id": "DOC-API-9", "destino_principal": "Fluxo_Padrao"}
    simular_rotas({("GET", f"{PREFIXO}/documentos"): (200, [documento])})
    at = _abrir(HISTORICO)

    at.selectbox[0].select("DOC-API-9").run()

    assert at.info[0].value == "Detalhes indisponíveis para este documento."
