from html import escape

from utils.formatadores import normalizar_prioridade, rotular_prioridade

CONFIANCA_ALTA = 0.85
CONFIANCA_MEDIA = 0.75

COR_DA_EMERGENCIA = "#C62828"
COR_POR_PRIORIDADE = {
    "EMERGENCIA": COR_DA_EMERGENCIA,
    "URGENTE": "#C2410C",
    "ROTINA": "#1B7F4B",
}
COR_POR_NIVEL_DE_CONFIANCA = {
    "alta": "#1B7F4B",
    "media": "#B45309",
    "baixa": COR_DA_EMERGENCIA,
}
COR_DO_TEXTO_POR_NIVEL_DE_CONFIANCA = {
    "alta": "green",
    "media": "orange",
    "baixa": "red",
}

ESTILO_DO_SELO = (
    "display:inline-block;color:#FFFFFF;font-weight:700;font-size:1.15rem;"
    "letter-spacing:0.04em;padding:0.35rem 1.1rem;border-radius:999px;"
)
ESTILO_DO_ALERTA_DE_EMERGENCIA = (
    f"border:4px solid {COR_DA_EMERGENCIA};background:#FDECEA;border-radius:12px;padding:1.1rem 1.3rem;"
)
ESTILO_DO_TITULO_DA_EMERGENCIA = "color:#8E1B1B;font-size:1.6rem;font-weight:800;line-height:1.25;"
ESTILO_DO_TEXTO_DA_EMERGENCIA = "color:#3B1212;margin-top:0.5rem;"
ESTILO_DA_FAIXA_DO_PLANTAO = (
    f"background:{COR_DA_EMERGENCIA};color:#FFFFFF;font-weight:700;border-radius:8px;"
    "padding:0.7rem 1rem;margin-top:0.8rem;"
)


def nivel_de_confianca(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= CONFIANCA_ALTA:
        return "alta"
    if score >= CONFIANCA_MEDIA:
        return "media"
    return "baixa"


def cor_da_prioridade(prioridade: str | None) -> str | None:
    nivel = normalizar_prioridade(prioridade)
    return COR_POR_PRIORIDADE[nivel] if nivel else None


def cor_da_confianca(score: float | None) -> str | None:
    nivel = nivel_de_confianca(score)
    return COR_POR_NIVEL_DE_CONFIANCA[nivel] if nivel else None


def texto_colorido_da_confianca(score: float | None) -> str | None:
    nivel = nivel_de_confianca(score)
    if nivel is None:
        return None
    return f":{COR_DO_TEXTO_POR_NIVEL_DE_CONFIANCA[nivel]}[**{score:.0%}**]"


def montar_selo_de_prioridade(prioridade: str | None) -> str | None:
    nivel = normalizar_prioridade(prioridade)
    if nivel is None:
        return None
    rotulo = escape(rotular_prioridade(nivel).upper())
    return f'<span style="{ESTILO_DO_SELO}background:{COR_POR_PRIORIDADE[nivel]};">{rotulo}</span>'


def montar_alerta_de_emergencia(titulo: str, justificativa: str | None, mensagem_do_plantao: str | None) -> str:
    partes = [
        f'<div style="{ESTILO_DO_ALERTA_DE_EMERGENCIA}">',
        f'<div style="{ESTILO_DO_TITULO_DA_EMERGENCIA}">🚨 {escape(titulo)}</div>',
    ]
    if justificativa:
        partes.append(f'<div style="{ESTILO_DO_TEXTO_DA_EMERGENCIA}">{escape(justificativa)}</div>')
    if mensagem_do_plantao:
        partes.append(f'<div style="{ESTILO_DA_FAIXA_DO_PLANTAO}">{escape(mensagem_do_plantao)}</div>')
    partes.append("</div>")
    return "".join(partes)