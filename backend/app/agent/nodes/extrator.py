import json
from typing import Any

from app.agent.harness import texto_clinico_sem_metadados
from app.agent.llm import obter_cliente_llm
from app.agent.prompts.extracao import PROMPT_EXTRACAO_SYSTEM, PROMPT_EXTRACAO_USER
from app.agent.state import GraphState


def _ler_resposta_json(conteudo: str) -> dict[str, Any]:
    texto = conteudo.strip()
    if texto.startswith("```"):
        linhas = texto.splitlines()
        texto = "\n".join(linhas[1:-1])
    dados = json.loads(texto)
    if not isinstance(dados, dict):
        raise ValueError("A resposta da LLM precisa ser um objeto JSON.")
    return dados


def _normalizar_medicamento(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Cada medicamento extraído precisa ser um objeto JSON.")
    return {
        "medicamento": item["medicamento"],
        "dosagem": item["dosagem"],
        "posologia": item["posologia"],
    }


def _contexto_identificacao_publico(state: GraphState) -> dict[str, Any]:
    cadastro = state.get("identificacao_cadastral") or {}
    extraido = state.get("identificacao_documento") or {}
    contexto = {}
    for entidade in ("paciente", "medico_solicitante"):
        dados = cadastro.get(entidade)
        if dados:
            contexto[entidade] = {
                chave: valor for chave, valor in dados.items() if chave != "registro_id"
            }
        else:
            contexto[entidade] = extraido.get(entidade) or {}
    return contexto


def node_extracao(state: GraphState) -> GraphState:
    """Extrai os dados somente pela LLM; erro de provedor ou schema interrompe a triagem."""
    texto = texto_clinico_sem_metadados(state["documento_texto"])
    identificacao_contexto = _contexto_identificacao_publico(state)
    cliente = obter_cliente_llm()
    resposta = cliente.invoke(
        [
            ("system", PROMPT_EXTRACAO_SYSTEM),
            (
                "human",
                PROMPT_EXTRACAO_USER.format(
                    documento_texto=texto,
                    identificacao_contexto=json.dumps(
                        identificacao_contexto, ensure_ascii=False
                    ),
                ),
            ),
        ]
    )
    if not isinstance(resposta.content, str):
        raise ValueError("A resposta da LLM precisa ser texto JSON.")
    dados = _ler_resposta_json(resposta.content)
    medicamentos = dados.get("medicamentos", [])
    if not isinstance(medicamentos, list):
        raise ValueError("O campo medicamentos da resposta da LLM precisa ser uma lista.")
    dados_identificacao = state.get("identificacao_documento") or {}
    paciente_identificado = dados_identificacao.get("paciente") or {}
    medico_identificado = dados_identificacao.get("medico_solicitante") or {}
    dados_extraidos = {
        "paciente": {
            "nome": dados["paciente_nome"] or paciente_identificado.get("nome"),
            "idade": (
                paciente_identificado.get("idade")
                if paciente_identificado.get("idade") is not None
                else dados["paciente_idade"]
            ),
        },
        "medico_solicitante": {
            "nome": dados["medico_nome"] or medico_identificado.get("nome"),
            "crm": dados["medico_crm"] or medico_identificado.get("crm"),
        },
        "exame_realizado": dados["exame_realizado"],
        "diagnostico_principal": dados["diagnostico_principal"],
        "cid_sugerido": dados["cid_sugerido"],
        "medicamentos": [_normalizar_medicamento(item) for item in medicamentos],
        "metodo": "llm_generativa",
    }

    evidencias_campos = {}
    valores = {
        "paciente.nome": dados_extraidos["paciente"]["nome"],
        "paciente.idade": dados_extraidos["paciente"]["idade"],
        "medico_solicitante.nome": dados_extraidos["medico_solicitante"]["nome"],
        "medico_solicitante.crm": dados_extraidos["medico_solicitante"]["crm"],
        "exame_realizado": dados_extraidos["exame_realizado"],
        "diagnostico_principal": dados_extraidos["diagnostico_principal"],
        "cid_sugerido": dados_extraidos["cid_sugerido"],
        "medicamentos": dados_extraidos["medicamentos"],
    }
    for caminho, valor in valores.items():
        literal = str(valor).strip() if valor is not None else ""
        inicio = texto.casefold().find(literal.casefold()) if literal else -1
        evidencias_campos[caminho] = {
            "valor": valor,
            "trecho": texto[inicio : inicio + len(literal)] if inicio >= 0 else None,
            "inicio": inicio if inicio >= 0 else None,
            "fim": inicio + len(literal) if inicio >= 0 else None,
            "status": "trecho_encontrado" if inicio >= 0 else "ausente_ou_sem_suporte",
            "confianca": None,
        }

    return {
        **state,
        "dados_extraidos": dados_extraidos,
        "evidencias_campos": evidencias_campos,
        "paciente": dados_extraidos["paciente"],
        "medico_solicitante": dados_extraidos["medico_solicitante"],
        "exame_realizado": dados_extraidos["exame_realizado"],
        "diagnostico_principal": dados_extraidos["diagnostico_principal"],
        "cid_sugerido": dados_extraidos["cid_sugerido"],
        "status": "extraido",
    }
