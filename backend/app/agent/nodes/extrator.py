import json
import re
from typing import Dict, Any
from app.agent.state import GraphState
from app.config.settings import settings
from app.config.logger import logger
from app.agent.prompts.extracao import (
    PROMPT_EXTRACAO_SYSTEM,
    PROMPT_EXTRACAO_USER,
)


def _extrair_deterministico(texto: str) -> Dict[str, Any]:
    """Plano C: Extrator baseado em padrões de expressões regulares médicas (SCRUM-58)."""
    # 1. Paciente
    match_paciente = re.search(r"(?:Paciente|Nome|Para)\s*:\s*([A-Za-zÀ-ÿ\s]{3,40})(?:\n|,|\.|\r|$)", texto, re.IGNORECASE)
    nome_paciente = match_paciente.group(1).strip() if match_paciente else None

    # Idade somente quando aparece explicitamente; não derivar de data de nascimento.
    match_idade = re.search(r"(\d{1,3})\s*(?:anos|ano|a\b)", texto, re.IGNORECASE)
    idade = int(match_idade.group(1)) if match_idade else None

    # 2. Médico & CRM
    match_medico = re.search(r"(?:Dr[a]?\.?|Médico|Solicitante|Profissional)\s*:\s*([A-Za-zÀ-ÿ\s]{3,40})(?:\n|,|\.|\r|-|$)", texto, re.IGNORECASE)
    nome_medico = match_medico.group(1).strip() if match_medico else None

    match_crm = re.search(r"CRM[^\d]*(\d{4,8}(?:-[A-Za-z]{2})?)", texto, re.IGNORECASE)
    crm = match_crm.group(1).strip().upper() if match_crm else None

    # 3. CID
    match_cid = re.search(r"CID[^\w]*([A-Z]\d{2}(?:\.\d{1,2})?)", texto, re.IGNORECASE)
    cid = match_cid.group(1).upper() if match_cid else None

    # Diagnóstico e exame são copiados apenas quando aparecem em rótulos explícitos.
    def _valor_rotulado(rotulos: str) -> str | None:
        match = re.search(rf"(?:{rotulos})\s*[:\-]\s*([^\n\r]+)", texto, re.IGNORECASE)
        return match.group(1).strip(" .;,") if match else None

    diagnostico = _valor_rotulado(r"diagn[oó]stico(?: principal)?|conclus[aã]o")
    exame = _valor_rotulado(r"exame(?: realizado)?|procedimento")

    return {
        "paciente": {
            "nome": nome_paciente,
            "idade": idade,
        },
        "medico_solicitante": {
            "nome": nome_medico,
            "crm": crm,
        },
        "exame_realizado": exame,
        "diagnostico_principal": diagnostico,
        "cid_sugerido": cid,
        "metodo": "regex_heuristico",
    }


def node_extracao(state: GraphState) -> GraphState:
    """Nó 3: Extração semântica estruturada via LLM com fallback resiliente (SCRUM-58)."""
    texto = state.get("documento_texto") or ""

    dados_extraidos = None
    from app.agent.llm import obter_cliente_llm
    llm = obter_cliente_llm()
    if llm:
        try:
            mensagens = [
                ("system", PROMPT_EXTRACAO_SYSTEM),
                ("human", PROMPT_EXTRACAO_USER.format(documento_texto=texto[:4000])),
            ]
            resposta = llm.invoke(mensagens)
            conteudo = resposta.content
            if isinstance(conteudo, str):
                conteudo_limpo = conteudo.strip().strip("```json").strip("```").strip()
                parsed = json.loads(conteudo_limpo)
                det = _extrair_deterministico(texto)
                paciente_nome = parsed.get("paciente_nome") or det["paciente"].get("nome")
                paciente_idade = parsed.get("paciente_idade") or det["paciente"].get("idade")
                medico_nome = parsed.get("medico_nome") or det["medico_solicitante"].get("nome")
                medico_crm = parsed.get("medico_crm") or det["medico_solicitante"].get("crm")
                exame = parsed.get("exame_realizado") or det.get("exame_realizado")
                diag = parsed.get("diagnostico_principal") or det.get("diagnostico_principal")
                cid = parsed.get("cid_sugerido") or det.get("cid_sugerido")
                medicamentos = parsed.get("medicamentos") or []

                def _normalizar_medicamento(item):
                    if isinstance(item, str):
                        return {"medicamento": item, "dosagem": None, "posologia": None}
                    if isinstance(item, dict):
                        return {
                            "medicamento": item.get("medicamento"),
                            "dosagem": item.get("dosagem"),
                            "posologia": item.get("posologia"),
                        }
                    return None

                dados_extraidos = {
                    "paciente": {
                        "nome": paciente_nome,
                        "idade": paciente_idade,
                    },
                    "medico_solicitante": {
                        "nome": medico_nome,
                        "crm": medico_crm,
                    },
                    "exame_realizado": exame,
                    "diagnostico_principal": diag,
                    "cid_sugerido": cid,
                    "medicamentos": [m for item in medicamentos if (m := _normalizar_medicamento(item))],
                    "metodo": "llm_generativa",
                }
        except Exception as e:
            logger.warning(f"Falha ao executar LLM no nó de extração: {e}. Acionando Plano C (Fallback).")
            dados_extraidos = None

    if not dados_extraidos:
        dados_extraidos = _extrair_deterministico(texto)

    dados_dict = dados_extraidos
    evidencias_campos = {}
    for caminho, valor in {
        "paciente.nome": (dados_dict.get("paciente") or {}).get("nome"),
        "paciente.idade": (dados_dict.get("paciente") or {}).get("idade"),
        "medico_solicitante.nome": (dados_dict.get("medico_solicitante") or {}).get("nome"),
        "medico_solicitante.crm": (dados_dict.get("medico_solicitante") or {}).get("crm"),
        "exame_realizado": dados_dict.get("exame_realizado"),
        "diagnostico_principal": dados_dict.get("diagnostico_principal"),
        "cid_sugerido": dados_dict.get("cid_sugerido"),
        "medicamentos": dados_dict.get("medicamentos", []),
    }.items():
        literal = str(valor).strip() if valor is not None else ""
        inicio = texto.casefold().find(literal.casefold()) if literal else -1
        evidencias_campos[caminho] = {
            "valor": valor,
            "trecho": texto[inicio:inicio + len(literal)] if inicio >= 0 else None,
            "inicio": inicio if inicio >= 0 else None,
            "fim": inicio + len(literal) if inicio >= 0 else None,
            "status": "trecho_encontrado" if inicio >= 0 else "ausente_ou_sem_suporte",
            "confianca": None,
        }

    return {
        **state,
        "dados_extraidos": dados_extraidos,
        "evidencias_campos": evidencias_campos,
        "paciente": dados_extraidos.get("paciente"),
        "medico_solicitante": dados_extraidos.get("medico_solicitante"),
        "exame_realizado": dados_extraidos.get("exame_realizado"),
        "diagnostico_principal": dados_extraidos.get("diagnostico_principal"),
        "cid_sugerido": dados_extraidos.get("cid_sugerido"),
        "status": "extraido",
    }
