"""Valida schema, suporte textual por campo e regras clínicas determinísticas."""

from typing import Any

from pydantic import ValidationError

from app.agent.state import GraphState
from app.schemas.classificacao import TipoDocumento
from app.schemas.dados_extraidos import DadosExtraidos
from app.agent.nodes.validadores_clinicos import validar_dados_extraidos
from app.agent.normalizacao_texto import localizar_trecho


def _evidenciar(valor: Any, texto: str) -> dict[str, Any]:
    if valor is None or not isinstance(valor, (str, int, float)):
        return {"status": "ausente", "trecho": None, "inicio": None, "fim": None}
    intervalo = localizar_trecho(texto, str(valor).strip())
    if intervalo is None:
        return {"status": "sem_suporte_textual", "trecho": None, "inicio": None, "fim": None}
    inicio, fim = intervalo
    return {"status": "trecho_encontrado", "trecho": texto[inicio:fim], "inicio": inicio, "fim": fim}


def node_validador(state: GraphState) -> GraphState:
    """Bloqueia valores sem suporte; evidência OCR não confirma a imagem fonte."""
    bruto = dict(state.get("dados_extraidos") or {})
    bruto.pop("metodo", None)
    medico = dict(bruto.get("medico_solicitante") or {})
    if "crm_uf" not in medico and medico.get("crm"):
        medico["crm_uf"] = medico.pop("crm")
    bruto["medico_solicitante"] = medico

    erros_schema: list[str] = []
    try:
        dados = DadosExtraidos.model_validate(bruto)
    except ValidationError as erro:
        erros_schema = [item["msg"] for item in erro.errors()]
        dados = DadosExtraidos()

    texto = state.get("documento_texto") or ""
    dados_dict = dados.model_dump()
    evidencias = {
        "paciente.nome": _evidenciar((dados_dict.get("paciente") or {}).get("nome"), texto),
        "paciente.idade": _evidenciar((dados_dict.get("paciente") or {}).get("idade"), texto),
        "medico_solicitante.nome": _evidenciar((dados_dict.get("medico_solicitante") or {}).get("nome"), texto),
        "medico_solicitante.crm_uf": _evidenciar((dados_dict.get("medico_solicitante") or {}).get("crm_uf"), texto),
        "exame_realizado": _evidenciar(dados_dict.get("exame_realizado"), texto),
        "diagnostico_principal": _evidenciar(dados_dict.get("diagnostico_principal"), texto),
        "cid_sugerido": _evidenciar(dados_dict.get("cid_sugerido"), texto),
    }
    for indice, medicamento in enumerate(dados_dict.get("medicamentos", [])):
        evidencias[f"medicamentos.{indice}.medicamento"] = _evidenciar(medicamento.get("medicamento"), texto)
        evidencias[f"medicamentos.{indice}.dosagem"] = _evidenciar(medicamento.get("dosagem"), texto)
        evidencias[f"medicamentos.{indice}.posologia"] = _evidenciar(medicamento.get("posologia"), texto)
    bloqueados = [campo for campo, evidencia in evidencias.items() if evidencia["status"] == "sem_suporte_textual"]
    erros_clinicos: list[str] = []
    tipo = state.get("tipo_documento")
    if tipo:
        try:
            tipo_enum = TipoDocumento(tipo)
            erros_clinicos = validar_dados_extraidos(dados, tipo_enum)
        except ValueError:
            erros_clinicos.append(f"Tipo documental não reconhecido para validação: {tipo}.")

    tipo_arquivo = (state.get("tipo_arquivo") or "").lower()
    fonte_textual = tipo_arquivo in {"texto", "json"}
    fonte_verificavel = fonte_textual and bool(state.get("referencia_fonte"))
    validacao_fonte = {
        "campos_com_trecho": [k for k, v in evidencias.items() if v["status"] == "trecho_encontrado"],
        "campos_sem_suporte": bloqueados,
        "fonte_original_disponivel": bool(state.get("referencia_fonte")),
        "fonte_verificada": fonte_verificavel,
        "texto_ocr_eh_prova_da_imagem": False,
    }
    precisa_revisao = bool(erros_schema or erros_clinicos or bloqueados or not fonte_verificavel)
    motivos = erros_schema + erros_clinicos
    if bloqueados:
        motivos.append("Há valores extraídos sem correspondência literal no texto de origem.")
    if not fonte_verificavel:
        motivos.append("A evidência textual ainda não foi verificada contra uma fonte legível e localizável.")

    # Valores sem correspondência literal não podem seguir como se estivessem confirmados.
    for campo in bloqueados:
        if campo.startswith("paciente.") and dados_dict.get("paciente"):
            dados_dict["paciente"][campo.split(".", 1)[1]] = None
        elif campo.startswith("medico_solicitante.") and dados_dict.get("medico_solicitante"):
            dados_dict["medico_solicitante"][campo.split(".", 1)[1]] = None
        elif campo.startswith("medicamentos."):
            _, indice, atributo = campo.split(".", 2)
            dados_dict["medicamentos"][int(indice)][atributo] = None
        else:
            dados_dict[campo] = None

    medico_para_servico = dict(dados_dict.get("medico_solicitante") or {})
    if "crm_uf" in medico_para_servico:
        medico_para_servico["crm"] = medico_para_servico.pop("crm_uf")

    return {
        **state,
        "dados_extraidos": dados_dict,
        "paciente": dados_dict.get("paciente"),
        "medico_solicitante": medico_para_servico,
        "exame_realizado": dados_dict.get("exame_realizado"),
        "diagnostico_principal": dados_dict.get("diagnostico_principal"),
        "cid_sugerido": dados_dict.get("cid_sugerido"),
        "medicamentos": dados_dict.get("medicamentos", []),
        "evidencias_campos": evidencias,
        "campos_bloqueados": bloqueados,
        "validacao_schema": {"valido": not erros_schema, "erros": erros_schema},
        "validacao_fonte": validacao_fonte,
        "inconsistencias": [*state.get("inconsistencias", []), *motivos],
        "requer_auditoria_humana": state.get("requer_auditoria_humana", False) or precisa_revisao,
        "motivo_revisao": "; ".join(motivos) if motivos else None,
        "etapa_revisao": "validacao" if precisa_revisao else None,
        "status": "validado" if not precisa_revisao else "revisao_necessaria",
    }
