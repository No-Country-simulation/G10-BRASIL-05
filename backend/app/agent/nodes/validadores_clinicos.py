import re

from app.schemas.classificacao import TipoDocumento
from app.schemas.dados_extraidos import DadosExtraidos


_UFS_BRASILEIRAS = frozenset(
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
        "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
        "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
)
_PADRAO_CRM = re.compile(
    r"^(?:CRM-(?P<uf_documento>[A-Z]{2})\s+(?P<numero_documento>\d+)"
    r"|(?P<numero_normalizado>\d+)-(?P<uf_normalizada>[A-Z]{2}))$",
    re.IGNORECASE,
)
_PADRAO_CID10 = re.compile(r"^[A-Z]\d{2}(?:\.\d{1,2})?$", re.IGNORECASE)

_CAMPOS_OBRIGATORIOS_POR_TIPO = {
    TipoDocumento.RECEITA: (
        "paciente.nome",
        "medico_solicitante.nome",
        "medico_solicitante.crm_uf",
    ),
    TipoDocumento.LAUDO: ("paciente.nome", "exame_realizado"),
    TipoDocumento.GUIA_TISS: (
        "paciente.nome",
        "medico_solicitante.nome",
        "medico_solicitante.crm_uf",
        "exame_realizado",
    ),
    TipoDocumento.RELATORIO_ALTA: ("paciente.nome", "diagnostico_principal"),
    TipoDocumento.ATESTADO: (
        "paciente.nome",
        "medico_solicitante.nome",
        "medico_solicitante.crm_uf",
    ),
}


def validar_crm(valor: object) -> bool:
    """Valida o formato CRM-UF sem consultar a existência do registro."""
    if valor is None:
        return True
    if not isinstance(valor, str):
        return False

    correspondencia = _PADRAO_CRM.fullmatch(valor.strip())
    if correspondencia is None:
        return False

    uf = correspondencia.group("uf_documento") or correspondencia.group(
        "uf_normalizada"
    )
    return uf.upper() in _UFS_BRASILEIRAS


def validar_cid10(valor: object) -> bool:
    """Valida a sintaxe do CID-10, sem consultar um catálogo de códigos."""
    if valor is None:
        return True
    if not isinstance(valor, str):
        return False
    return _PADRAO_CID10.fullmatch(valor.strip()) is not None


def validar_idade_plausivel(idade: object) -> bool:
    """Aceita idade inteira entre 0 e 120 anos, inclusive."""
    if idade is None:
        return True
    return type(idade) is int and 0 <= idade <= 120


def validar_dados_extraidos(
    dados: DadosExtraidos,
    tipo_documento: TipoDocumento,
) -> list[str]:
    """Retorna todas as inconsistências encontradas nos dados extraídos."""
    erros: list[str] = []

    for caminho in _CAMPOS_OBRIGATORIOS_POR_TIPO[tipo_documento]:
        valor = _obter_campo(dados, caminho)
        if not _texto_presente(valor):
            erros.append(
                f"O campo '{caminho}' é obrigatório para {tipo_documento.value}."
            )

    if tipo_documento == TipoDocumento.RECEITA and not any(
        _texto_presente(item.medicamento) and _texto_presente(item.dosagem)
        for item in dados.medicamentos
    ):
        erros.append(
            "RECEITA requer ao menos um medicamento com nome e dosagem."
        )

    crm_uf = (
        dados.medico_solicitante.crm_uf
        if dados.medico_solicitante is not None
        else None
    )
    if _texto_presente(crm_uf) and not validar_crm(crm_uf):
        erros.append("O campo 'medico_solicitante.crm_uf' tem formato inválido.")

    if _texto_presente(dados.cid_sugerido) and not validar_cid10(
        dados.cid_sugerido
    ):
        erros.append("O campo 'cid_sugerido' não está no formato CID-10 esperado.")

    idade = dados.paciente.idade if dados.paciente is not None else None
    if not validar_idade_plausivel(idade):
        erros.append("O campo 'paciente.idade' deve ser um inteiro entre 0 e 120.")

    return erros


def _obter_campo(dados: DadosExtraidos, caminho: str) -> object:
    if caminho == "paciente.nome":
        return dados.paciente.nome if dados.paciente is not None else None
    if caminho == "medico_solicitante.nome":
        return (
            dados.medico_solicitante.nome
            if dados.medico_solicitante is not None
            else None
        )
    if caminho == "medico_solicitante.crm_uf":
        return (
            dados.medico_solicitante.crm_uf
            if dados.medico_solicitante is not None
            else None
        )
    if caminho == "exame_realizado":
        return dados.exame_realizado
    if caminho == "diagnostico_principal":
        return dados.diagnostico_principal
    raise ValueError(f"Campo obrigatório não mapeado: {caminho}")


def _texto_presente(valor: object) -> bool:
    return isinstance(valor, str) and bool(valor.strip())
