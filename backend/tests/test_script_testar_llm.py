import importlib.util
from pathlib import Path

_CAMINHO_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "testar_llm.py"
_spec = importlib.util.spec_from_file_location("testar_llm", _CAMINHO_SCRIPT)
testar_llm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(testar_llm)


def test_sem_chave_orienta_configuracao_e_falha(capsys):
    codigo = testar_llm.executar_testes(None, None)

    assert codigo == 1
    assert "GOOGLE_API_KEY" in capsys.readouterr().out


def test_chamadas_de_texto_imagem_e_pdf_respondem(capsys):
    imagens_recebidas = []

    def cliente_visao(instrucao, imagens):
        imagens_recebidas.append(imagens)
        return "Receita transcrita"

    codigo = testar_llm.executar_testes(lambda mensagens: "OK", cliente_visao)

    saida = capsys.readouterr().out
    assert codigo == 0
    assert "3/3 chamadas responderam" in saida
    assert [imagens[0]["mime_type"] for imagens in imagens_recebidas] == ["image/png", "image/jpeg"]


def test_falha_em_uma_chamada_retorna_erro(capsys):
    def cliente_visao_com_erro(instrucao, imagens):
        raise RuntimeError("modelo não suporta imagem")

    codigo = testar_llm.executar_testes(lambda mensagens: "OK", cliente_visao_com_erro)

    saida = capsys.readouterr().out
    assert codigo == 1
    assert "[FALHOU] Visão: receita_escaneada.png" in saida
    assert "1/3 chamadas responderam" in saida


def test_resposta_vazia_conta_como_falha(capsys):
    codigo = testar_llm.executar_testes(lambda mensagens: "   ", lambda instrucao, imagens: "texto")

    assert codigo == 1
    assert "[FALHOU] Chamada de texto: resposta vazia" in capsys.readouterr().out
