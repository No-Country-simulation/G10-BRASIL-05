import base64

import pytest

from utils.whatsapp import (
    NIVEL_AVISO,
    NIVEL_ERRO,
    NIVEL_SUCESSO,
    decodificar_qrcode,
    descrever_conexao,
    normalizar_numero,
    validar_numero,
)


@pytest.mark.parametrize(
    "numero, esperado",
    [("5511999999999", "5511999999999"), ("+55 (11) 99999-9999", "5511999999999"), ("  55 11 99999 9999 ", "5511999999999")],
)
def test_normaliza_o_numero(numero, esperado):
    assert normalizar_numero(numero) == esperado


@pytest.mark.parametrize("numero", ["5511999999999", "+55 (11) 99999-9999", "1234567890", "123456789012345"])
def test_aceita_numeros_validos(numero):
    assert validar_numero(numero) is None


@pytest.mark.parametrize("numero", ["55", "123456789", "1234567890123456"])
def test_recusa_numero_com_tamanho_invalido(numero):
    assert "10 a 15 dígitos" in validar_numero(numero)


@pytest.mark.parametrize("numero", ["", "   ", "+()-"])
def test_pede_o_numero_quando_vazio(numero):
    assert "Informe o número" in validar_numero(numero)


@pytest.mark.parametrize("numero", ["abc", "55119999x9999", "55-11-99999-9999!", "５５１１９９９９９９９９９"])
def test_recusa_numero_com_letras_ou_simbolos(numero):
    assert "apenas números" in validar_numero(numero)


@pytest.mark.parametrize(
    "status, nivel, titulo",
    [
        ({"conectado": True, "estado": "open"}, NIVEL_SUCESSO, "conectado"),
        ({"conectado": False, "estado": "connecting"}, NIVEL_AVISO, "QR Code"),
        ({"conectado": False, "estado": "close"}, NIVEL_ERRO, "desconectado"),
        ({"conectado": False, "estado": "not_found"}, NIVEL_ERRO, "não criada"),
        ({"conectado": False, "estado": "offline"}, NIVEL_ERRO, "Evolution API indisponível"),
        ({"conectado": False, "estado": "erro"}, NIVEL_ERRO, "Estado desconhecido: erro"),
        ({}, NIVEL_ERRO, "Estado desconhecido: desconhecido"),
    ],
)
def test_descreve_a_conexao(status, nivel, titulo):
    resultado_nivel, resultado_titulo, _ = descrever_conexao(status)

    assert resultado_nivel == nivel
    assert titulo.lower() in resultado_titulo.lower()


def test_conectado_prevalece_sobre_o_estado_informado():
    assert descrever_conexao({"conectado": True, "estado": "qualquer"})[0] == NIVEL_SUCESSO


@pytest.mark.parametrize("prefixo", ["", "data:image/png;base64,"])
def test_decodifica_o_qrcode_com_ou_sem_prefixo(prefixo):
    imagem = b"\x89PNG-conteudo"

    assert decodificar_qrcode(prefixo + base64.b64encode(imagem).decode()) == imagem


@pytest.mark.parametrize("conteudo", ["isto não é base64!", "abc", ""])
def test_qrcode_invalido_levanta_erro(conteudo):
    with pytest.raises(ValueError):
        decodificar_qrcode(conteudo)
