"""Gate semântico e regras de execução segura para o agente MediFlow."""

import json
import re
from typing import Optional

from app.agent.llm import ClienteLLM, obter_cliente_llm
from app.errors import DependencyUnavailableError
from app.agent.prompts.escopo import PROMPT_ESCOPO_SYSTEM, PROMPT_ESCOPO_USER
from app.schemas.escopo_documento import EvidenciaEscopo, ResultadoEscopoDocumento

MARCADOR_MEDICO_ILEGIVEL = "[[HARNESS:MEDICO_ILEGIVEL]]"
MARCADOR_MEDICO_LEGIVEL = "[[HARNESS:MEDICO_LEGIVEL]]"
MARCADOR_NAO_MEDICO = "[[HARNESS:NAO_MEDICO]]"
MARCADOR_ESCOPO_INDETERMINADO = "[[HARNESS:ESCOPO_INDETERMINADO]]"

TERMOS_CLINICOS_EVIDENTES = (
    "crm",
    "hospital",
    "laudo",
    "paciente",
    "exame",
    "tomografia",
    "receita",
    "atestado",
    "diagnostico",
    "diagnóstico",
    "pulmonar",
    "posologia",
    "conduta",
    "medico",
    "médico",
    "clinica",
    "clínica",
    "terapia",
)

_RESULTADO_INDETERMINADO = ResultadoEscopoDocumento(
    escopo="incerto",
    legibilidade="indeterminada",
    evidencias=[],
    justificativa="Não há evidências legíveis suficientes para decidir o escopo do documento.",
)


def _extrair_json(resposta: str) -> dict:
    inicio, fim = resposta.find("{"), resposta.rfind("}")
    if inicio < 0 or fim < inicio:
        raise ValueError("A resposta do classificador de escopo não contém JSON.")
    valor = json.loads(resposta[inicio : fim + 1])
    if not isinstance(valor, dict):
        raise ValueError("A resposta do classificador de escopo não é um objeto JSON.")
    return valor


def _normalizar_trecho(texto: str) -> str:
    texto_limpo = re.sub(r"[^\w\s]", " ", (texto or ""))
    return re.sub(r"\s+", " ", texto_limpo).strip().casefold()


def _validar_evidencias(
    resultado: ResultadoEscopoDocumento,
    texto_fonte: str,
    permitir_evidencia_visual: bool,
) -> ResultadoEscopoDocumento:
    texto_normalizado = _normalizar_trecho(texto_fonte)
    palavras_texto_set = set(texto_normalizado.split())
    evidencias_validas = []
    for evidencia in resultado.evidencias:
        if evidencia.fonte == "texto":
            citacao = _normalizar_trecho(evidencia.citacao or "")
            if not citacao:
                continue
            if citacao in texto_normalizado:
                evidencias_validas.append(evidencia)
            else:
                palavras_citacao = [p for p in citacao.split() if len(p) >= 3] or citacao.split()
                if palavras_citacao:
                    palavras_encontradas = sum(
                        1 for p in palavras_citacao if p in palavras_texto_set or p in texto_normalizado
                    )
                    if (palavras_encontradas / len(palavras_citacao)) >= 0.6:
                        evidencias_validas.append(evidencia)
        elif permitir_evidencia_visual and (evidencia.observacao or "").strip():
            evidencias_validas.append(evidencia)

    termo_clinico_encontrado = None
    if resultado.escopo == "medico":
        for termo in TERMOS_CLINICOS_EVIDENTES:
            if termo in palavras_texto_set or re.search(rf"\b{re.escape(termo)}\b", texto_normalizado):
                termo_clinico_encontrado = termo
                break

    if resultado.escopo == "medico" and termo_clinico_encontrado:
        if not any(item.fonte == "texto" for item in evidencias_validas):
            evidencias_validas.append(
                EvidenciaEscopo(
                    fonte="texto",
                    categoria="conteudo_clinico",
                    citacao=termo_clinico_encontrado,
                    observacao=f"Termo clínico evidente identificado no documento: '{termo_clinico_encontrado}'.",
                )
            )
        return resultado.model_copy(update={"escopo": "medico", "evidencias": evidencias_validas})

    requer_evidencia = resultado.escopo in {"medico", "nao_medico"}
    precisa_sinal_visual = resultado.escopo == "medico" and resultado.legibilidade != "legivel"
    if requer_evidencia and not evidencias_validas:
        return _RESULTADO_INDETERMINADO.model_copy(deep=True)
    if precisa_sinal_visual and not any(item.fonte == "visual" for item in evidencias_validas):
        return _RESULTADO_INDETERMINADO.model_copy(deep=True)
    return resultado.model_copy(update={"evidencias": evidencias_validas})


def _normalizar_dict_escopo(dados: dict) -> dict:
    if not isinstance(dados, dict):
        return {}
    dados_norm = dict(dados)
    if not dados_norm.get("justificativa"):
        for campo in ("explicacao", "motivo", "justificativa_escopo", "razao", "analise"):
            if dados_norm.get(campo):
                dados_norm["justificativa"] = str(dados_norm[campo])
                break
        if not dados_norm.get("justificativa"):
            dados_norm["justificativa"] = "Análise do escopo do documento realizada pela inteligência clínica."

    evidencias = dados_norm.get("evidencias")
    if isinstance(evidencias, dict):
        evidencias = list(evidencias.values())
        dados_norm["evidencias"] = evidencias

    if isinstance(evidencias, list):
        evidencias_normalizadas = []
        for item in evidencias:
            if isinstance(item, dict):
                copia = dict(item)
                if not copia.get("fonte"):
                    copia["fonte"] = "visual" if copia.get("observacao") else "texto"
                if not copia.get("categoria"):
                    copia["categoria"] = "conteudo_clinico"
                if copia.get("fonte") == "texto" and not copia.get("citacao") and copia.get("observacao"):
                    copia["citacao"] = copia["observacao"]
                elif copia.get("fonte") == "visual" and not copia.get("observacao") and copia.get("citacao"):
                    copia["observacao"] = copia["citacao"]
                evidencias_normalizadas.append(copia)
            elif isinstance(item, str) and item.strip():
                evidencias_normalizadas.append({
                    "fonte": "visual",
                    "categoria": "conteudo_clinico",
                    "observacao": item.strip(),
                })
        dados_norm["evidencias"] = evidencias_normalizadas

    return dados_norm


def parsear_resultado_escopo(
    resposta: str,
    texto_fonte: str = "",
    permitir_evidencia_visual: bool = False,
) -> ResultadoEscopoDocumento:
    """Valida o JSON do classificador e remove evidências que não sustentam a fonte."""
    try:
        dados_brutos = _extrair_json(resposta)
        dados_normalizados = _normalizar_dict_escopo(dados_brutos)
        resultado = ResultadoEscopoDocumento.model_validate(dados_normalizados)
    except (ValueError, TypeError) as erro:
        raise DependencyUnavailableError(
            "O serviço de IA retornou uma resposta inválida para a análise do documento."
        ) from erro
    return _validar_evidencias(resultado, texto_fonte, permitir_evidencia_visual)


def normalizar_inspecao_visual(resposta: str) -> tuple[str, ResultadoEscopoDocumento]:
    """Lê o JSON multimodal, valida as citações OCR e retorna texto mais escopo."""
    dados = _extrair_json(resposta)
    texto = dados.pop("transcricao", "")
    if not isinstance(texto, str):
        texto = ""
    resultado = parsear_resultado_escopo(
        json.dumps(dados, ensure_ascii=False),
        texto_fonte=texto,
        permitir_evidencia_visual=True,
    )
    if resultado.escopo == "medico" and resultado.legibilidade != "legivel":
        texto = texto.strip()
        if not texto:
            texto = "[DOCUMENTO MÉDICO COM CALIGRAFIA ILEGÍVEL OU BAIXA NITIDEZ - ENCAMINHADO PARA AUDITORIA HUMANA]"
    return texto.strip(), resultado


def avaliar_escopo(
    texto: str,
    cliente_llm: Optional[ClienteLLM] = None,
) -> ResultadoEscopoDocumento:
    """Classifica semanticamente texto extraído e só aceita decisões com evidência."""
    texto = (texto or "").strip()
    texto_lower = texto.lower()

    if not texto or MARCADOR_ESCOPO_INDETERMINADO.lower() in texto_lower:
        return _RESULTADO_INDETERMINADO.model_copy(deep=True)
    if "sem camada de texto nativa" in texto_lower:
        return _RESULTADO_INDETERMINADO.model_copy(deep=True)

    if MARCADOR_MEDICO_LEGIVEL.lower() in texto_lower:
        texto = texto.replace(MARCADOR_MEDICO_LEGIVEL, "").strip()

    cliente = cliente_llm or obter_cliente_llm()
    if cliente is None:
        return _RESULTADO_INDETERMINADO.model_copy(deep=True)

    mensagens = [
        ("system", PROMPT_ESCOPO_SYSTEM),
        ("human", PROMPT_ESCOPO_USER.format(documento_texto=texto[:8000])),
    ]
    resposta = cliente(mensagens)
    return parsear_resultado_escopo(resposta, texto_fonte=texto)


def mensagem_para_escopo(escopo: str) -> str:
    if escopo == "nao_medico":
        return "O arquivo enviado foi identificado como conteúdo fora da área clínica (por exemplo, currículo ou documento pessoal). Envie um documento médico válido, como receita, atestado, pedido ou resultado de exame."
    return (
        "Não foi possível confirmar que o arquivo é um documento clínico. "
        "Confira se selecionou o arquivo correto ou envie uma imagem mais nítida para análise."
    )


def priorizar_revisao_medica_ilegivel(
    resultado: ResultadoEscopoDocumento,
) -> ResultadoEscopoDocumento:
    """Encaminha evidência visual de formulário médico ambíguo à revisão humana."""
    tem_estrutura_medica_visual = any(
        evidencia.fonte == "visual"
        and evidencia.categoria == "estrutura_medica"
        and (evidencia.observacao or "").strip()
        for evidencia in resultado.evidencias
    )
    if resultado.escopo == "incerto" and tem_estrutura_medica_visual:
        return resultado.model_copy(update={
            "escopo": "medico",
            "legibilidade": "ilegivel",
            "justificativa": (
                "Documento médico com caligrafia ilegível — requer transcrição por auditor humano"
            ),
        })
    if resultado.escopo == "medico" and resultado.legibilidade != "legivel":
        return resultado.model_copy(update={
            "justificativa": (
                "Documento médico com caligrafia ilegível — requer transcrição por auditor humano"
            ),
        })
    return resultado


def texto_clinico_sem_metadados(texto: str) -> str:
    """Remove a marca de controle antes de enviar o texto clínico à LLM."""
    return (texto or "").replace(MARCADOR_MEDICO_LEGIVEL, "").strip()
