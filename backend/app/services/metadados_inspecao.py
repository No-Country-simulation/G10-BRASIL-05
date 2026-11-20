"""Extração não persistente e validada de metadados para a inspeção."""

import json
import re
from typing import Any

from app.agent.llm import obter_cliente_llm
from app.agent.prompts.metadados_inspecao import (
    PROMPT_METADADOS_SYSTEM,
    PROMPT_METADADOS_USER,
)
from app.schemas.metadados_inspecao import MetadadosInspecaoDocumento


def _normalizar_texto(valor: str) -> str:
    return re.sub(r"\s+", " ", valor or "").strip().casefold()


def extrair_campos_rotulados(texto: str) -> list[dict[str, str]]:
    """Converte rótulos comuns em pares mesmo quando o OCR achata as linhas."""
    campos: list[dict[str, str]] = []
    texto = re.sub(r"\s+", " ", (texto or "").replace("：", ":")).strip()
    padroes_rotulos = [
        r"Assinado\s+Eletronicamente\s+por",
        r"Respons[aá]vel\s+T[eé]cnic[ao]",
        r"Data\s+de\s+cadastro",
        r"M[eé]dico(?:\(a\))?(?:\s+Dr\(a\))?",
        r"Valores\s+de\s+Refer[eê]ncia",
        r"Tempo\s+de\s+Protrombina",
        r"Paciente",
        r"Categoria",
        r"Passaporte",
        r"Idade",
        r"Sa[ií]da",
        r"CNPJ",
        r"CPF",
        r"CRM",
        r"Material",
        r"M[eé]todo",
        r"Resultado",
        r"Atividade",
        r"INR",
        r"O\.?\s*S\.?",
        r"RG",
        r"Em\s+\d{2}/\d{2}/\d{2,4}",
    ]
    padrao = re.compile(
        r"(?<![\w])(?P<rotulo>" + "|".join(padroes_rotulos) + r")\s*:\s*",
        re.IGNORECASE,
    )
    ocorrencias = list(padrao.finditer(texto))
    for indice, ocorrencia in enumerate(ocorrencias):
        inicio_valor = ocorrencia.end()
        fim_valor = ocorrencias[indice + 1].start() if indice + 1 < len(ocorrencias) else len(texto)
        rotulo = ocorrencia.group("rotulo").strip()
        valor = texto[inicio_valor:fim_valor].strip(" \t-*•;,")
        if rotulo.casefold().startswith("médico") or rotulo.casefold().startswith("medico"):
            valor = re.split(r"\s+TEMPO\s+DE\s+PROTROMBINA\b", valor, maxsplit=1, flags=re.IGNORECASE)[0]
            valor = valor.strip(" \t-*•;,")
        if valor:
            campos.append({"rotulo": rotulo, "valor": valor})
    return campos


def _json_da_resposta(resposta: str) -> dict[str, Any]:
    inicio, fim = resposta.find("{"), resposta.rfind("}")
    if inicio < 0 or fim < inicio:
        raise ValueError("A extração de metadados não retornou JSON.")
    dados = json.loads(resposta[inicio : fim + 1])
    if not isinstance(dados, dict):
        raise ValueError("A extração de metadados não retornou um objeto JSON.")
    return dados


def normalizar_metadados_inspecao(
    resposta: str,
    texto_fonte: str,
) -> MetadadosInspecaoDocumento:
    """Descarta campos sem citação verificável no texto extraído do documento."""
    try:
        dados = _json_da_resposta(resposta)
        if isinstance(dados.get("metadados_documento"), dict):
            dados = dados["metadados_documento"]
        else:
            # A inspeção visual pode devolver os campos no objeto JSON raiz junto
            # com escopo/transcrição; seleciona apenas o contrato de metadados.
            nomes_campos = set(MetadadosInspecaoDocumento.model_fields)
            dados = {campo: valor for campo, valor in dados.items() if campo in nomes_campos}
        resultado = MetadadosInspecaoDocumento.model_validate(dados)
    except (ValueError, TypeError):
        return MetadadosInspecaoDocumento()

    fonte = _normalizar_texto(texto_fonte)
    valores = resultado.model_dump()
    evidencias_validas: dict[str, str] = {}
    campos_de_valor = set(valores) - {"evidencias"}
    for campo, valor in resultado.evidencias.items():
        citacao = _normalizar_texto(valor)
        if campo in valores and valores[campo] is not None and citacao and citacao in fonte:
            evidencias_validas[campo] = valor
        elif campo in valores:
            valores[campo] = None
    for campo in campos_de_valor - evidencias_validas.keys():
        valores[campo] = None
    valores["evidencias"] = evidencias_validas
    try:
        return MetadadosInspecaoDocumento.model_validate(valores)
    except (ValueError, TypeError):
        return MetadadosInspecaoDocumento()


def extrair_metadados_documento(texto: str) -> MetadadosInspecaoDocumento:
    """Extrai campos administrativos de texto com evidência literal; falha fechada."""
    texto = (texto or "").strip()
    if not texto:
        return MetadadosInspecaoDocumento()

    cliente = obter_cliente_llm()
    if cliente is None:
        return MetadadosInspecaoDocumento()
    try:
        resposta = cliente([
            ("system", PROMPT_METADADOS_SYSTEM),
            ("human", PROMPT_METADADOS_USER.format(documento_texto=texto[:12000])),
        ])
        return normalizar_metadados_inspecao(resposta, texto)
    except Exception:
        return MetadadosInspecaoDocumento()
