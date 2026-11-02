import json
import re
from typing import Dict, Any, Optional
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

    # Idade (ou cálculo a partir de data de nascimento)
    match_idade = re.search(r"(\d{1,3})\s*(?:anos|ano|a\b)", texto, re.IGNORECASE)
    idade = int(match_idade.group(1)) if match_idade else None
    if idade is None:
        match_nasc = re.search(r"(?:nascimento|nasc\.?|dt\.?\s*nasc(?:imento)?)\s*[:.]?\s*(\d{2})[/.-](\d{2})[/.-](\d{4})", texto, re.IGNORECASE)
        if match_nasc:
            from datetime import datetime
            ano_nasc = int(match_nasc.group(3))
            ano_atual = datetime.now().year
            if 1900 <= ano_nasc <= ano_atual:
                idade = ano_atual - ano_nasc

    # 2. Médico & CRM
    match_medico = re.search(r"(?:Dr[a]?\.?|Médico|Solicitante|Profissional)\s*:\s*([A-Za-zÀ-ÿ\s]{3,40})(?:\n|,|\.|\r|-|$)", texto, re.IGNORECASE)
    nome_medico = match_medico.group(1).strip() if match_medico else None

    match_crm = re.search(r"CRM[^\d]*(\d{4,8}(?:-[A-Za-z]{2})?)", texto, re.IGNORECASE)
    crm = match_crm.group(1).strip().upper() if match_crm else None

    # 3. CID
    match_cid = re.search(r"CID[^\w]*([A-Z]\d{2}(?:\.\d{1,2})?)", texto, re.IGNORECASE)
    cid = match_cid.group(1).upper() if match_cid else None

    # 4. Diagnóstico & Exame
    texto_lower = texto.lower()
    if "tromboembolismo" in texto_lower or "tep" in texto_lower or "embolia" in texto_lower:
        diagnostico = "Tromboembolismo Pulmonar Agudo (TEP)"
        cid = cid or "I26.9"
        exame = "Tomografia de Tórax com protocolo para TEP"
    elif "pneumonia" in texto_lower:
        diagnostico = "Pneumonia Adquirida na Comunidade"
        cid = cid or "J18.9"
        exame = "Radiografia de Tórax"
    elif "hipertensao" in texto_lower or "losartana" in texto_lower:
        diagnostico = "Hipertensão Arterial Sistêmica (HAS)"
        cid = cid or "I10"
        exame = "Consulta de Rotina"
    elif "agendamento" in texto_lower or "consulta" in texto_lower:
        diagnostico = "Consulta Médica / Acompanhamento"
        exame = "Consulta Ambulatorial / PSF"
    else:
        diagnostico = "Avaliação Clínica em Triagem" if len(texto_lower) > 30 else None
        exame = "Avaliação Clínica"

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
                    "metodo": "llm_generativa",
                }
        except Exception as e:
            logger.warning(f"Falha ao executar LLM no nó de extração: {e}. Acionando Plano C (Fallback).")
            dados_extraidos = None

    if not dados_extraidos:
        dados_extraidos = _extrair_deterministico(texto)

    return {
        **state,
        "dados_extraidos": dados_extraidos,
        "paciente": dados_extraidos.get("paciente"),
        "medico_solicitante": dados_extraidos.get("medico_solicitante"),
        "exame_realizado": dados_extraidos.get("exame_realizado"),
        "diagnostico_principal": dados_extraidos.get("diagnostico_principal"),
        "cid_sugerido": dados_extraidos.get("cid_sugerido"),
        "status": "extraido",
    }
