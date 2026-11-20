import re
from typing import List, Optional

from pydantic import ValidationError

from app.agent.llm import ClienteLLM, obter_cliente_llm
from app.agent.prompts.extracao import (
    PROMPT_EXTRACAO_SYSTEM,
    PROMPT_EXTRACAO_USER,
    VERSAO as VERSAO_PROMPT,
)
from app.agent.state import GraphState
from app.agent.texto import extrair_json, normalizar
from app.config.logger import logger
from app.schemas.dados_extraidos import (
    DadosExtraidos,
    MedicamentoDosagem,
    MedicoSolicitante,
    PacienteExtraido,
)

LIMITE_CARACTERES_PROMPT = 4000

_PALAVRA_NOME = r"(?!CRM\b|CID\b)[A-Za-zÀ-ÿ]+"
_NOME = rf"({_PALAVRA_NOME}(?:[ \t]+{_PALAVRA_NOME}){{1,5}})"
_PADRAO_PACIENTE = re.compile(rf"\bPaciente\s*:\s*{_NOME}", re.IGNORECASE)
_PADRAO_IDADE = re.compile(r"\b(\d{1,3})\s*anos\b", re.IGNORECASE)
_PADRAO_MEDICO = re.compile(rf"\b(?:M[ée]dic[oa](?:\s+solicitante)?\s*:\s*)?(Dra?\.\s*{_NOME})", re.IGNORECASE)
_PADRAO_CRM = re.compile(r"\bCRM\s*[-:/]?\s*(?:([A-Z]{2})\s*[-:/]?\s*)?(\d{4,8})(?:\s*[-/]\s*([A-Z]{2}))?", re.IGNORECASE)
_PADRAO_CID = re.compile(r"\bCID(?:-?10)?\s*[:\-]?\s*([A-Z]\d{2}(?:\.\d{1,2})?)\b", re.IGNORECASE)
_PADRAO_DIAGNOSTICO = re.compile(
    r"\b(?:Diagn[óo]stico(?:\s+principal)?|Hip[óo]tese\s+diagn[óo]stica|Conclus[ãa]o)\s*:\s*([^\n]+?)(?=[.;,]?\s*(?:CID\b|$))",
    re.IGNORECASE | re.MULTILINE,
)
_PADRAO_EXAME = re.compile(r"\b(?:Exame(?:\s+realizado)?\s*:\s*([^\n]+)|Laudo\s+de\s+([^\n:.]+))", re.IGNORECASE)
_PADRAO_MEDICAMENTO = re.compile(
    r"([A-ZÀ-Ý][a-zà-ÿ]+(?:[ \t]+[A-ZÀ-Ýa-zà-ÿ]+){0,2})[ \t]+(\d+(?:[.,]\d+)?[ \t]?(?:mg|mcg|g|ml|UI))\b",
)


def _primeiro_grupo(padrao: re.Pattern, texto: str) -> Optional[str]:
    correspondencia = padrao.search(texto)
    if correspondencia is None:
        return None
    valor = next((grupo for grupo in correspondencia.groups() if grupo), None)
    return valor.strip().rstrip(".,;") if valor else None


def _extrair_crm(texto: str) -> Optional[str]:
    """Retorna o CRM no formato NUMERO-UF; sem UF explícita, retorna None."""
    correspondencia = _PADRAO_CRM.search(texto)
    if correspondencia is None:
        return None
    uf_antes, numero, uf_depois = correspondencia.groups()
    uf = uf_antes or uf_depois
    return f"{numero}-{uf.upper()}" if uf else None


def _extrair_medicamentos(texto: str) -> List[MedicamentoDosagem]:
    return [
        MedicamentoDosagem(medicamento=nome.strip(), dosagem=dosagem.strip())
        for nome, dosagem in _PADRAO_MEDICAMENTO.findall(texto)
    ]


def _extrair_deterministico(texto: str) -> DadosExtraidos:
    """Plano C: extrator por expressões regulares; só preenche o que está escrito no texto."""
    idade = _primeiro_grupo(_PADRAO_IDADE, texto)
    nome_medico = _primeiro_grupo(_PADRAO_MEDICO, texto)
    crm_uf = _extrair_crm(texto)
    cid = _primeiro_grupo(_PADRAO_CID, texto)

    return DadosExtraidos(
        paciente=PacienteExtraido(
            nome=_primeiro_grupo(_PADRAO_PACIENTE, texto),
            idade=int(idade) if idade else None,
        ),
        medico_solicitante=MedicoSolicitante(nome=nome_medico, crm_uf=crm_uf),
        exame_realizado=_primeiro_grupo(_PADRAO_EXAME, texto),
        diagnostico_principal=_primeiro_grupo(_PADRAO_DIAGNOSTICO, texto),
        cid_sugerido=cid.upper() if cid else None,
        medicamentos=_extrair_medicamentos(texto),
    )


def _presente_no_texto(valor: Optional[str], texto_normalizado: str) -> bool:
    return valor is not None and normalizar(valor).strip() in texto_normalizado


def _numero_presente_no_texto(valor: Optional[str], texto: str) -> bool:
    numero = re.sub(r"\D", "", valor or "")
    return bool(numero) and numero in re.sub(r"\D", " ", texto).split()


def _descartar_valores_inventados(dados: DadosExtraidos, texto: str) -> DadosExtraidos:
    """Anula nomes, CRM, CID e medicamentos que a LLM devolveu mas não aparecem no documento."""
    texto_normalizado = normalizar(texto)
    paciente = dados.paciente or PacienteExtraido()
    medico = dados.medico_solicitante or MedicoSolicitante()

    return dados.model_copy(
        update={
            "paciente": paciente.model_copy(
                update={"nome": paciente.nome if _presente_no_texto(paciente.nome, texto_normalizado) else None}
            ),
            "medico_solicitante": medico.model_copy(
                update={
                    "nome": medico.nome if _presente_no_texto(medico.nome, texto_normalizado) else None,
                    "crm_uf": medico.crm_uf if _numero_presente_no_texto(medico.crm_uf, texto) else None,
                }
            ),
            "cid_sugerido": dados.cid_sugerido if _presente_no_texto(dados.cid_sugerido, texto_normalizado) else None,
            "medicamentos": [
                item for item in dados.medicamentos if _presente_no_texto(item.medicamento, texto_normalizado)
            ],
        }
    )


def _extrair_com_llm(cliente_llm: ClienteLLM, texto: str) -> Optional[DadosExtraidos]:
    """Plano B: extração via LLM com saída validada pelo schema; None em caso de falha."""
    mensagens = [
        ("system", PROMPT_EXTRACAO_SYSTEM),
        ("human", PROMPT_EXTRACAO_USER.format(documento_texto=texto[:LIMITE_CARACTERES_PROMPT])),
    ]
    try:
        resposta = cliente_llm(mensagens)
        dados = DadosExtraidos.model_validate(extrair_json(resposta))
        return _descartar_valores_inventados(dados, texto)
    except (ValueError, ValidationError) as erro:
        logger.warning(f"Resposta da LLM fora do schema de extração: {erro}. Acionando Plano C (Fallback).")
    except Exception as erro:
        logger.warning(f"Falha ao executar LLM no nó de extração: {erro}. Acionando Plano C (Fallback).")
    return None


def criar_node_extracao(cliente_llm: Optional[ClienteLLM]):
    """Cria o nó de extração com o cliente LLM informado (None usa apenas o fallback)."""

    def node_extracao(state: GraphState) -> GraphState:
        """Nó 3: Extração de entidades clínicas via LLM (Plano B) com fallback por regex (Plano C) (SCRUM-58)."""
        texto = state.get("documento_texto") or ""

        dados = _extrair_com_llm(cliente_llm, texto) if cliente_llm else None
        metodo = "llm_generativa"
        if dados is None:
            dados = _extrair_deterministico(texto)
            metodo = "regex_heuristico"

        dados_dict = dados.model_dump(mode="json")
        return {
            **state,
            "dados_extraidos": {
                **dados_dict,
                "metodo": metodo,
                "versao_prompt": VERSAO_PROMPT if metodo == "llm_generativa" else None,
            },
            "paciente": dados_dict["paciente"],
            "medico_solicitante": dados_dict["medico_solicitante"],
            "exame_realizado": dados_dict["exame_realizado"],
            "diagnostico_principal": dados_dict["diagnostico_principal"],
            "cid_sugerido": dados_dict["cid_sugerido"],
            "medicamentos": dados_dict["medicamentos"],
            "status": "extraido",
        }

    return node_extracao


node_extracao = criar_node_extracao(obter_cliente_llm())
