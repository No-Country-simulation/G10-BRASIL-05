"""Valida schema, suporte textual por campo e regras clínicas determinísticas."""

from typing import Any

from pydantic import ValidationError

from app.agent.state import GraphState
from app.schemas.classificacao import TipoDocumento
from app.schemas.dados_extraidos import DadosExtraidos
from app.agent.nodes.validadores_clinicos import validar_dados_extraidos
from app.agent.normalizacao_texto import (
    localizar_trecho,
    localizar_trecho_cpf,
    normalizar_cpf,
    validar_cpf,
)


def _evidenciar(valor: Any, texto: str, *, campo_cpf: bool = False) -> dict[str, Any]:
    if valor is None or not isinstance(valor, (str, int, float)):
        return {"status": "ausente", "trecho": None, "inicio": None, "fim": None}
    intervalo = localizar_trecho(texto, str(valor).strip())
    if intervalo is None and campo_cpf:
        intervalo = localizar_trecho_cpf(texto, str(valor))
    if intervalo is None:
        return {"status": "sem_suporte_textual", "trecho": None, "inicio": None, "fim": None}
    inicio, fim = intervalo
    return {"status": "trecho_encontrado", "trecho": texto[inicio:fim], "inicio": inicio, "fim": fim}


def node_validador(state: GraphState) -> GraphState:
    """Bloqueia valores sem suporte; evidência OCR não confirma a imagem fonte."""
    if state.get("cpf_validacao_falhou"):
        tentativas = state.get("cpf_tentativas_releitura")
        if tentativas:
            motivo = (
                f"Não foi possível confirmar um CPF válido após {tentativas} tentativas de releitura visual."
            )
        else:
            motivo = (
                "CPF ausente, ilegível ou inválido. Confirme os 11 dígitos no documento."
            )
        return {
            **state,
            "status": "revisao_necessaria",
            "requer_auditoria_humana": True,
            "etapa_revisao": "validacao",
            "motivo_revisao": motivo,
            "inconsistencias": [*state.get("inconsistencias", []), motivo],
        }

    bruto = dict(state.get("dados_extraidos") or {})
    bruto.pop("metodo", None)
    paciente_bruto = bruto.get("paciente")
    if isinstance(paciente_bruto, dict):
        paciente = dict(paciente_bruto)
        paciente["cpf"] = normalizar_cpf(paciente.get("cpf"))
        bruto["paciente"] = paciente
    medico = dict(bruto.get("medico_solicitante") or {})
    crm = medico.pop("crm", None)
    if "crm_uf" not in medico and crm:
        medico["crm_uf"] = crm
    bruto["medico_solicitante"] = medico

    erros_schema: list[str] = []
    try:
        dados = DadosExtraidos.model_validate(bruto)
    except ValidationError:
        erros_schema = [
            "Não foi possível validar os dados clínicos extraídos. Confira as informações no documento."
        ]
        dados = DadosExtraidos()

    texto = state.get("documento_texto") or ""
    dados_dict = dados.model_dump()
    evidencias = {
        "paciente.nome": _evidenciar((dados_dict.get("paciente") or {}).get("nome"), texto),
        "paciente.cpf": _evidenciar(
            (dados_dict.get("paciente") or {}).get("cpf"), texto, campo_cpf=True
        ),
        "paciente.idade": _evidenciar((dados_dict.get("paciente") or {}).get("idade"), texto),
        "medico_solicitante.nome": _evidenciar((dados_dict.get("medico_solicitante") or {}).get("nome"), texto),
        "medico_solicitante.crm_uf": _evidenciar((dados_dict.get("medico_solicitante") or {}).get("crm_uf"), texto),
        "exame_realizado": _evidenciar(dados_dict.get("exame_realizado"), texto),
        "diagnostico_principal": _evidenciar(dados_dict.get("diagnostico_principal"), texto),
        "cid_sugerido": _evidenciar(dados_dict.get("cid_sugerido"), texto),
    }
    cpf_validado_visualmente = (state.get("cpf_releitura_visual") and validar_cpf(
        (dados_dict.get("paciente") or {}).get("cpf")
    ))
    if cpf_validado_visualmente:
        evidencias["paciente.cpf"] = {
            "status": "releitura_visual",
            "trecho": None,
            "inicio": None,
            "fim": None,
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
            erros_clinicos.append("Não foi possível validar a categoria do documento.")

    tipo_arquivo = (state.get("tipo_arquivo") or "").lower()
    fonte_textual = tipo_arquivo in {"texto", "json"}
    tipos_com_fonte_original = {"texto", "json", "imagem", "image", "pdf"}
    referencia_fonte = state.get("referencia_fonte")
    fonte_original_disponivel = (
        tipo_arquivo in tipos_com_fonte_original and bool(referencia_fonte)
    )
    fonte_verificada_visualmente = bool(state.get("fonte_verificada_visualmente"))
    fonte_verificada = (
        fonte_textual and fonte_original_disponivel
    ) or fonte_verificada_visualmente
    validacao_fonte = {
        "campos_com_trecho": [k for k, v in evidencias.items() if v["status"] == "trecho_encontrado"],
        "campos_sem_suporte": bloqueados,
        "fonte_original_disponivel": fonte_original_disponivel,
        "fonte_verificada": fonte_verificada,
        "fonte_verificada_visualmente": fonte_verificada_visualmente,
        "texto_ocr_extraido": bool(texto.strip()),
        "texto_ocr_eh_prova_da_imagem": False,
    }
    precisa_revisao = bool(
        erros_schema or erros_clinicos or bloqueados or not fonte_verificada
    )
    motivos = erros_schema + erros_clinicos
    contem_manuscrito = bool(state.get("contem_manuscrito") or bruto.get("contem_manuscrito"))
    if contem_manuscrito and not fonte_verificada_visualmente:
        precisa_revisao = True
        motivos.append("Documento contém dados manuscritos; requer validação e conferência humana.")
    if bloqueados:
        motivos.append("Há valores extraídos sem correspondência literal no texto de origem.")
    if not fonte_original_disponivel:
        motivos.append("Documento original não disponível para conferência.")
    elif tipo_arquivo in {"imagem", "image", "pdf"} and not fonte_verificada_visualmente:
        motivos.append(
            "Texto extraído do documento visual ainda precisa ser conferido no original."
        )
    elif not fonte_verificada:
        motivos.append("Fonte do documento ainda não foi verificada.")

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
