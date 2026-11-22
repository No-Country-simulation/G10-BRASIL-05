"""Filtros puros usados pela tela de análise."""
from datetime import datetime


def obter_documentos_demo() -> list[dict]:
    """Documentos sintéticos usados para demonstrar os canais na tela de análise."""
    exemplos = [
        ("DEMO-WPP-001", "WPP_demo_receita_001.jpg", "WhatsApp", "RECEITA", "ROTINA", "Paciente fictício 01", "2026-11-22T10:15:00"),
        ("DEMO-WPP-002", "WPP_demo_atestado_002.pdf", "WhatsApp", "ATESTADO", "ROTINA", "Paciente fictício 02", "2026-11-22T09:40:00"),
        ("DEMO-WPP-003", "WPP_demo_laudo_003.pdf", "WhatsApp", "LAUDO", "URGENTE", "Paciente fictício 03", "2026-11-22T08:55:00"),
        ("DEMO-INT-001", "Interno_demo_ficha_001.pdf", "Interno", "FICHA_ATENDIMENTO", "URGENTE", "Paciente fictício 04", "2026-11-22T10:05:00"),
        ("DEMO-INT-002", "Interno_demo_laudo_002.pdf", "Interno", "LAUDO", "EMERGENCIA", "Paciente fictício 05", "2026-11-22T09:20:00"),
        ("DEMO-INT-003", "Interno_demo_receita_003.pdf", "Interno", "RECEITA", "ROTINA", "Paciente fictício de demonstração com nome propositalmente muito longo para validar o limite visual da coluna Paciente", "2026-11-22T08:30:00"),
    ]
    return [
        {
            "documento_id": documento_id,
            "arquivo": arquivo,
            "nome_original": arquivo,
            "paciente_nome": paciente,
            "paciente_cpf": "-",
            "data_hora": datetime.fromisoformat(criado_em).strftime("%d/%m/%Y %H:%M"),
            "data_iso": criado_em,
            "status": "em_auditoria" if documento_id == "DEMO-INT-002" else "concluido",
            "status_processamento": "em_auditoria" if documento_id == "DEMO-INT-002" else "processado",
            "requer_auditoria_humana": documento_id == "DEMO-INT-002",
            "destino_principal": "Auditoria_Humana" if documento_id == "DEMO-INT-002" else "Fluxo_Padrao",
            "motivo_revisao": "Demonstração: dados clínicos requerem conferência humana." if documento_id == "DEMO-INT-002" else None,
            "canal_origem": canal,
            "tipo_documento": tipo,
            "nivel_prioridade": prioridade,
            "resultado": None,
            "erro": None,
            "etapa_atual": None,
        }
        for documento_id, arquivo, canal, tipo, prioridade, paciente, criado_em in exemplos
    ]


def corresponde_filtro(
    doc: dict,
    filtro_status: str,
    termo_busca: str,
    filtro_canal: str = "Todos",
) -> bool:
    """Indica se um documento atende ao filtro de status, canal e à busca textual."""
    if filtro_status != "Todos":
        status_esperado = {
            "Na fila": "na_fila",
            "Processando": "processando",
            "Concluído": "concluido",
            "Falhou": "falhou",
        }.get(filtro_status)
        if doc.get("status") != status_esperado:
            return False

    if filtro_canal != "Todos":
        canal_doc = (doc.get("canal_origem") or "").lower()
        filtro_canal_norm = filtro_canal.lower().replace(" ", "_")
        if (
            filtro_canal.lower() not in canal_doc
            and filtro_canal_norm not in canal_doc
        ):
            return False

    if termo_busca:
        campos = (
            doc.get("arquivo", ""),
            doc.get("nome_original", ""),
            doc.get("paciente_nome", ""),
            doc.get("paciente_cpf", ""),
            doc.get("documento_id", ""),
            doc.get("canal_origem", ""),
            doc.get("tipo_documento", ""),
        )
        if termo_busca.lower() not in " ".join(str(c) for c in campos).lower():
            return False

    return True
