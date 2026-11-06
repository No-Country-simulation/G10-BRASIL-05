from copy import deepcopy

from streamlit.testing.v1 import AppTest

# Formato devolvido hoje pela API de triagem (paciente como objeto, CRM em "crm")
RESPOSTA_DA_API = {
    "status": "processado",
    "documento_id": "DOC-1",
    "classificacao": {
        "tipo_documento": "Laudo de Exame de Imagem",
        "especialidade": "Radiologia / Pneumologia",
        "nivel_prioridade": "Urgente",
        "score_confianca_classificacao": 0.95,
    },
    "dados_extraidos": {
        "paciente": {"nome": "Carlos Eduardo Mendes", "idade": 52},
        "medico_solicitante": {"nome": "Dra. Renata Silveira", "crm": "145892-SP"},
        "exame_realizado": "Tomografia de Tórax",
        "diagnostico_principal": "Tromboembolismo Pulmonar Agudo (TEP)",
        "cid_sugerido": "I26.9",
    },
    "decisao_roteamento": {
        "destino_principal": "Fila_Emergencia_Medica",
        "requer_auditoria_humana": False,
        "justificativa_roteamento": "Achado crítico detectado.",
        "notificacao_gerada": {"canal": "Alerta_Plantao_Medico", "mensagem": "ALERTA URGENTE: DOC-1"},
    },
}

# Formato do schema DadosExtraidos (paciente como texto, CRM em "crm_uf", medicamentos)
DADOS_DO_SCHEMA = {
    "paciente": "Maria Silva",
    "medico_solicitante": {"nome": "João Souza", "crm_uf": "12345-SP"},
    "medicamentos": [
        {"medicamento": "Amoxicilina", "dosagem": "500 mg"},
        {"medicamento": None, "dosagem": None},
    ],
}


def _renderizar(nome_da_funcao: str, dado: dict) -> AppTest:
    def app(nome_da_funcao, dado):
        from components import cards

        getattr(cards, nome_da_funcao)(dado)

    return AppTest.from_function(app, args=(nome_da_funcao, dado)).run()


def _textos(at: AppTest) -> str:
    return "\n".join(elemento.value for elemento in at.markdown)


def test_mostra_o_resultado_no_formato_da_api():
    at = _renderizar("exibir_resultado_da_triagem", RESPOSTA_DA_API)

    texto = _textos(at)
    assert not at.exception
    assert "URGENTE: encaminhado para a fila de emergência médica" in texto
    assert "ALERTA URGENTE: DOC-1" in texto
    assert "**Laudo de Exame de Imagem**" in texto
    assert "**Urgente**" in texto
    assert "**Carlos Eduardo Mendes, 52 anos**" in texto
    assert "**Dra. Renata Silveira (CRM 145892-SP)**" in texto
    assert "**Tomografia de Tórax**" in texto


def test_mostra_dados_no_formato_do_schema_do_backend():
    at = _renderizar("exibir_dados_extraidos", DADOS_DO_SCHEMA)

    texto = _textos(at)
    assert not at.exception
    assert "**Maria Silva**" in texto
    assert "**João Souza (CRM 12345-SP)**" in texto
    assert "- Amoxicilina · 500 mg" in texto


def test_medicamento_sem_dados_nao_gera_item_vazio():
    at = _renderizar("exibir_dados_extraidos", DADOS_DO_SCHEMA)

    itens = [elemento.value for elemento in at.markdown if elemento.value.startswith("- ")]
    assert itens == ["- Amoxicilina · 500 mg"]


def test_dados_ausentes_mostram_nao_informado():
    at = _renderizar("exibir_dados_extraidos", {})

    assert not at.exception
    assert _textos(at).count("**Não informado**") == 4


def test_documento_de_rotina_aparece_como_aprovado():
    resposta = deepcopy(RESPOSTA_DA_API)
    resposta["decisao_roteamento"] = {
        "destino_principal": "Fluxo_Padrao",
        "requer_auditoria_humana": False,
        "justificativa_roteamento": "Sem pendências.",
        "notificacao_gerada": None,
    }

    at = _renderizar("exibir_resultado_da_triagem", resposta)

    assert "Rotina: aprovado automaticamente" in at.success[0].value


def test_destino_desconhecido_nao_quebra():
    resposta = deepcopy(RESPOSTA_DA_API)
    resposta["decisao_roteamento"]["destino_principal"] = "Destino_Novo"

    at = _renderizar("exibir_resultado_da_triagem", resposta)

    assert not at.exception
    assert "Destino não reconhecido" in at.info[0].value


def test_item_de_auditoria_da_api_funciona_sem_prioridade():
    # A fila de auditoria do backend não envia nivel_prioridade nem documento_texto
    item = {
        "documento_id": "DOC-3",
        "tipo_documento": "Receituario Medico",
        "score_confianca": 0.58,
        "dados_extraidos": RESPOSTA_DA_API["dados_extraidos"],
        "justificativa_roteamento": "CRM ausente.",
    }

    at = _renderizar("exibir_item_de_auditoria", item)

    assert not at.exception
    assert "CRM ausente." in at.warning[0].value
    assert ":red[**58%**]" in _textos(at)


def _renderizar_previa(nome_do_arquivo: str) -> AppTest:
    def app(nome_do_arquivo):
        import base64
        import io

        from components.cards import exibir_previa_do_arquivo

        class Arquivo(io.BytesIO):
            name = nome_do_arquivo
            size = 2048

        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        exibir_previa_do_arquivo(Arquivo(png))

    return AppTest.from_function(app, args=(nome_do_arquivo,)).run()


def test_previa_de_imagem_mostra_a_imagem():
    at = _renderizar_previa("receita.PNG")

    assert not at.exception
    assert len(at.get("image")) == 1
    assert not at.info


def test_previa_de_imagem_grande_fica_limitada_a_uma_altura_fixa():
    from components.cards import ALTURA_DA_PREVIA_EM_PIXELS

    at = _renderizar_previa("receita.png")

    caixa = next(bloco for bloco in at.main if bloco.type == "flex_container")
    assert caixa.proto.height_config.pixel_height == ALTURA_DA_PREVIA_EM_PIXELS
    assert [filho.type for filho in caixa.children.values()] == ["caption", "image"]
    assert "receita.png" in caixa.children[0].value


def test_previa_de_pdf_mostra_nome_e_tamanho():
    at = _renderizar_previa("laudo.PDF")

    assert not at.exception
    assert "laudo.PDF" in at.info[0].value
    assert "2.0 KB" in at.info[0].value
    assert not at.get("image")


def test_previa_de_texto_ou_json_nao_mostra_nada():
    at = _renderizar_previa("exame.json")

    assert not at.exception
    assert not at.info
    assert not at.get("image")


def _com_armazenamento(status: str | None) -> dict:
    resposta = deepcopy(RESPOSTA_DA_API)
    resposta["armazenamento_oci"] = {
        "bucket": "mediflow-documentos-clinicos",
        "caminho_objeto": "processados/urgentes/DOC-1.json",
        "status_backup": status,
    }
    return resposta


def test_mostra_onde_o_documento_foi_salvo():
    at = _renderizar("exibir_resultado_da_triagem", _com_armazenamento("sucesso"))

    assert not at.exception
    assert "mediflow-documentos-clinicos/processados/urgentes/DOC-1.json" in at.success[-1].value
    assert not at.error


def test_backup_com_falha_aparece_como_erro_e_nao_como_sucesso():
    at = _renderizar("exibir_resultado_da_triagem", _com_armazenamento("falha: timeout no OCI"))

    assert "backup não foi gravado" in at.error[0].value
    assert not any("Documento salvo" in s.value for s in at.success)


def test_armazenamento_local_avisa_que_o_oci_nao_foi_usado():
    at = _renderizar("exibir_resultado_da_triagem", _com_armazenamento("sucesso (local_simulado)"))

    assert "sem usar o OCI" in at.warning[0].value


def test_resposta_sem_armazenamento_nao_mostra_a_secao():
    at = _renderizar("exibir_resultado_da_triagem", RESPOSTA_DA_API)

    assert not at.error
    assert "Armazenamento" not in [s.value for s in at.subheader]


def test_alerta_de_urgencia_mostra_o_canal_do_plantao():
    resposta = deepcopy(RESPOSTA_DA_API)
    resposta["decisao_roteamento"]["notificacao_gerada"] = {
        "canal": "Alerta_Plantao_Medico",
        "mensagem": "ALERTA URGENTE: DOC-1",
    }

    at = _renderizar("exibir_resultado_da_triagem", resposta)

    assert "ALERTA URGENTE: DOC-1 (canal: Alerta_Plantao_Medico)" in _textos(at)
