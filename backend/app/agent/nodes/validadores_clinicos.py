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
_PREFIXO_CRM = re.compile(r"^CRM\b\s*[-/]?\s*", re.IGNORECASE)
_PADRAO_CRM = re.compile(
    r"^(?:(?P<uf_prefixo>[A-Z]{2})[\s/-]+)?"
    r"(?P<numero>\d+)(?:[\s/-]+(?P<uf_sufixo>[A-Z]{2}))?$",
    re.IGNORECASE,
)
_PADRAO_CID10 = re.compile(r"^[A-Z]\d{2}(?:\.\d{1,2})?$", re.IGNORECASE)

ROTULOS_CAMPOS_OBRIGATORIOS = {
    "paciente.nome": "Nome do paciente não identificado no documento.",
    "exame_realizado": "Exame realizado não identificado no documento.",
    "medico_solicitante.nome": "Nome do médico solicitante não identificado no documento.",
    "medico_solicitante.crm_uf": "CRM do médico solicitante não identificado no documento.",
    "diagnostico_principal": "Diagnóstico principal não identificado no documento.",
}

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

    valor_limpo = valor.strip()
    tem_prefixo_crm = bool(_PREFIXO_CRM.match(valor_limpo))
    valor_normalizado = _PREFIXO_CRM.sub("", valor_limpo, count=1)
    correspondencia = _PADRAO_CRM.fullmatch(valor_normalizado)
    if correspondencia is None:
        return False

    if correspondencia.group("uf_prefixo") and not tem_prefixo_crm:
        return False

    uf = correspondencia.group("uf_prefixo") or correspondencia.group("uf_sufixo")
    return uf is None or uf.upper() in _UFS_BRASILEIRAS


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
            erros.append(ROTULOS_CAMPOS_OBRIGATORIOS.get(
                caminho,
                "Informação clínica obrigatória não identificada no documento.",
            ))

    if tipo_documento == TipoDocumento.RECEITA and not any(
        _texto_presente(item.medicamento) and _texto_presente(item.dosagem)
        for item in dados.medicamentos
    ):
        erros.append(
            "Medicamento e dosagem não identificados na receita."
        )

    crm_uf = (
        dados.medico_solicitante.crm_uf
        if dados.medico_solicitante is not None
        else None
    )
    if _texto_presente(crm_uf) and not validar_crm(crm_uf):
        erros.append("O CRM do médico solicitante está em formato inválido.")

    if _texto_presente(dados.cid_sugerido) and not validar_cid10(
        dados.cid_sugerido
    ):
        erros.append("O CID informado está em formato inválido.")

    idade = dados.paciente.idade if dados.paciente is not None else None
    if not validar_idade_plausivel(idade):
        erros.append("A idade do paciente deve estar entre 0 e 120 anos.")

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
