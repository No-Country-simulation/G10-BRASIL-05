import base64
import json
from pathlib import Path
from typing import Any

from app.agent.harness import texto_clinico_sem_metadados
from app.agent.imagem_cpf import preparar_imagem_para_releitura
from app.agent.llm import obter_cliente_llm
from app.agent.normalizacao_texto import localizar_trecho_cpf, normalizar_cpf, validar_cpf
from app.agent.prompts.extracao import PROMPT_EXTRACAO_SYSTEM, PROMPT_EXTRACAO_USER
from app.agent.state import GraphState
from app.config.logger import logger

MAX_TENTATIVAS_RELEITURA_CPF = 10


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


def _reler_cpf_na_imagem(cliente: Any, estado: GraphState) -> tuple[str | None, int]:
    """Repete a leitura visual até validar ou atingir o limite de tentativas."""
    caminho = estado.get("referencia_fonte")
    if (estado.get("tipo_arquivo") or "").lower() not in {"imagem", "image"} or not caminho:
        return None, 0

    try:
        imagem = preparar_imagem_para_releitura(Path(caminho).read_bytes())
        from langchain_core.messages import HumanMessage
    except Exception as erro:
        # Não registrar imagem, caminho ou qualquer valor de CPF.
        logger.warning("Falha ao preparar imagem para releitura de CPF (%s).", type(erro).__name__)
        return None, 0

    mensagem = HumanMessage(content=[
        {
            "type": "text",
            "text": (
                "Leia somente o CPF do paciente que esteja visível nesta imagem. "
                "Transcreva os dígitos exatamente como aparecem; não complete, corrija, "
                "deduza nem altere dígitos para satisfazer validação. Se não estiver "
                'legível ou não existir, retorne {"paciente_cpf": null}. '
                'Retorne somente JSON: {"paciente_cpf": "texto visível" ou null}.'
            ),
        },
        {
            "type": "image_url",
            "image_url": {
                "url": "data:image/jpeg;base64,"
                + base64.b64encode(imagem).decode("ascii")
            },
        },
    ])
    total_tentativas = 0
    for tentativa in range(1, MAX_TENTATIVAS_RELEITURA_CPF + 1):
        total_tentativas = tentativa
        try:
            resposta = cliente.invoke([mensagem])
            if isinstance(resposta.content, str):
                cpf_lido = _ler_resposta_json(resposta.content).get("paciente_cpf")
                if validar_cpf(cpf_lido):
                    return normalizar_cpf(cpf_lido), total_tentativas
        except Exception as erro:
            # Não registrar imagem, caminho ou qualquer valor de CPF.
            logger.warning(
                "Falha na releitura visual de CPF, tentativa %d/%d (%s).",
                tentativa,
                MAX_TENTATIVAS_RELEITURA_CPF,
                type(erro).__name__,
            )
    return None, total_tentativas
    return None


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
    cpf_bruto = dados.get("paciente_cpf") or paciente_identificado.get("cpf")
    cpf_extraido = normalizar_cpf(cpf_bruto)
    cpf_releitura_visual = False
    tentativas_releitura = 0
    if not validar_cpf(cpf_bruto):
        cpf_extraido, tentativas_releitura = _reler_cpf_na_imagem(cliente, state)
        cpf_releitura_visual = cpf_extraido is not None

    cns_bruto = dados.get("paciente_cns")
    cns_extraido = None
    if cns_bruto:
        digitos_cns = "".join(c for c in str(cns_bruto) if c.isdigit())
        if len(digitos_cns) == 15:
            cns_extraido = digitos_cns

    contem_manuscrito = bool(dados.get("contem_manuscrito"))

    dados_extraidos = {
        "paciente": {
            "nome": dados["paciente_nome"] or paciente_identificado.get("nome"),
            "cpf": cpf_extraido,
            "cns": cns_extraido,
            "idade": (
                paciente_identificado.get("idade")
                if paciente_identificado.get("idade") is not None
                else dados["paciente_idade"]
            ),
            "data_nascimento": (
                paciente_identificado.get("data_nascimento")
                if paciente_identificado.get("data_nascimento")
                else dados.get("paciente_data_nascimento")
                or (identificacao_contexto.get("paciente") or {}).get("data_nascimento")
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
        "contem_manuscrito": contem_manuscrito,
    }

    evidencias_campos = {}
    valores = {
        "paciente.nome": dados_extraidos["paciente"]["nome"],
        "paciente.cpf": dados_extraidos["paciente"]["cpf"],
        "paciente.idade": dados_extraidos["paciente"]["idade"],
        "paciente.data_nascimento": dados_extraidos["paciente"]["data_nascimento"],
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
        if caminho == "paciente.cpf" and inicio < 0 and literal:
            intervalo = localizar_trecho_cpf(texto, literal)
            if intervalo:
                inicio, fim = intervalo
                literal = texto[inicio:fim]
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
        "cpf_releitura_visual": cpf_releitura_visual,
        "cpf_validacao_falhou": cpf_extraido is None,
        "cpf_tentativas_releitura": tentativas_releitura,
    }
