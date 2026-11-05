import pytest
from pydantic import ValidationError

from app.schemas.dados_extraidos import DadosExtraidos
from app.schemas.triagem import DecisaoAuditoriaRequest


def _payload(status_aprovacao, dados_corrigidos="ausente"):
    payload = {
        "status_aprovacao": status_aprovacao,
        "auditor_nome": "Dra. Ana Silva",
        "justificativa": "Revisão clínica concluída.",
    }
    if dados_corrigidos != "ausente":
        payload["dados_corrigidos"] = dados_corrigidos
    return payload


@pytest.mark.parametrize("status", ["aprovacao", "pendente", "", "APROVADO"])
def test_decisao_rejeita_status_fora_do_contrato(status):
    with pytest.raises(ValidationError):
        DecisaoAuditoriaRequest.model_validate(_payload(status))


@pytest.mark.parametrize(
    "dados_corrigidos",
    [
        "ausente",
        None,
        {},
        {"paciente": {}},
        {"medicamentos": [{}]},
        {"dados_desconhecidos": "valor"},
        {"paciente": {"idade": "cinquenta"}},
    ],
)
def test_decisao_corrigido_exige_dados_validos_e_nao_vazios(dados_corrigidos):
    with pytest.raises(ValidationError):
        DecisaoAuditoriaRequest.model_validate(
            _payload("corrigido", dados_corrigidos)
        )


@pytest.mark.parametrize("status", ["aprovado", "rejeitado"])
def test_decisao_aprovada_ou_rejeitada_nao_aceita_correcao(status):
    with pytest.raises(ValidationError):
        DecisaoAuditoriaRequest.model_validate(
            _payload(status, {"cid_sugerido": "I20.0"})
        )


@pytest.mark.parametrize(
    "dados_corrigidos",
    [
        {"cid_sugerido": "I20.0"},
        {"paciente": {"nome": "Maria Silva"}},
        {"medicamentos": [{"medicamento": "AAS", "dosagem": "100 mg"}]},
    ],
)
def test_decisao_corrigido_aceita_correcao_parcial_valida(dados_corrigidos):
    decisao = DecisaoAuditoriaRequest.model_validate(
        _payload("corrigido", dados_corrigidos)
    )

    assert isinstance(decisao.dados_corrigidos, DadosExtraidos)
