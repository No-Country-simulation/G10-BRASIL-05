from scripts.uso_oci import LIMITE_ALWAYS_FREE_BYTES, resumo_uso


def test_bucket_vazio():
    uso = resumo_uso(0, 0)

    assert uso["percentual"] == 0
    assert uso["alerta"] is False
    assert uso["limite_gb"] == 20


def test_abaixo_do_alerta():
    uso = resumo_uso(int(LIMITE_ALWAYS_FREE_BYTES * 0.5), 100)

    assert uso["percentual"] == 50
    assert uso["alerta"] is False


def test_a_partir_de_80_por_cento_alerta():
    uso = resumo_uso(int(LIMITE_ALWAYS_FREE_BYTES * 0.8), 100)

    assert uso["alerta"] is True


def test_converte_tamanho_para_mb():
    uso = resumo_uso(5 * 1024 ** 2, 3)

    assert uso["tamanho_mb"] == 5
    assert uso["objetos"] == 3
