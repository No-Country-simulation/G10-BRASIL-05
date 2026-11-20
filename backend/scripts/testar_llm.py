"""Testa a chave da LLM com uma chamada de texto e duas de visão (imagem e PDF escaneado) (SCRUM-47).

Pré-requisito: GOOGLE_API_KEY (ou OPENAI_API_KEY) definida no `.env` local, nunca versionado.
Uso, a partir da pasta backend/:
    python scripts/testar_llm.py
O script nunca imprime a chave; sai com código 0 se as três chamadas responderem.
"""

import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple

PASTA_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PASTA_BACKEND))

from app.agent.llm import (  # noqa: E402
    MODELO_PADRAO_GEMINI,
    MODELO_PADRAO_OPENAI,
    ClienteLLM,
    ClienteVisao,
    obter_cliente_llm,
    obter_cliente_visao,
)
from app.agent.prompts.transcricao import PROMPT_TRANSCRICAO  # noqa: E402
from app.config.settings import settings  # noqa: E402
from app.services.document_parser import DocumentParserService  # noqa: E402

PASTA_AMOSTRAS = PASTA_BACKEND.parent / "data" / "samples" / "escaneados"
AMOSTRAS_VISAO = ["receita_escaneada.png", "laudo_escaneado.pdf"]
PROMPT_TEXTO = [("human", "Responda apenas com a palavra OK.")]


def descrever_provedor() -> str:
    """Nome do provedor e do modelo configurados, sem expor a chave."""
    if settings.GOOGLE_API_KEY:
        return f"Gemini ({settings.LLM_MODEL or MODELO_PADRAO_GEMINI})"
    if settings.OPENAI_API_KEY:
        return f"OpenAI ({settings.LLM_MODEL or MODELO_PADRAO_OPENAI})"
    return "nenhum"


def _executar(nome: str, chamada: Callable[[], str]) -> Tuple[str, bool]:
    try:
        resposta = chamada().strip()
    except Exception as erro:
        print(f"[FALHOU] {nome}: {type(erro).__name__}: {erro}")
        return nome, False
    if not resposta:
        print(f"[FALHOU] {nome}: resposta vazia")
        return nome, False
    print(f"[OK] {nome}:\n{resposta}\n")
    return nome, True


def _chamada_visao(cliente_visao: ClienteVisao, arquivo: Path) -> Callable[[], str]:
    def chamar() -> str:
        documento = DocumentParserService.preparar_documento(arquivo.read_bytes(), arquivo.suffix, arquivo.name)
        return cliente_visao(PROMPT_TRANSCRICAO, [imagem.model_dump() for imagem in documento.imagens])

    return chamar


def executar_testes(
    cliente_llm: Optional[ClienteLLM],
    cliente_visao: Optional[ClienteVisao],
    pasta_amostras: Path = PASTA_AMOSTRAS,
) -> int:
    """Roda as chamadas de teste e devolve o código de saída do script."""
    if cliente_llm is None or cliente_visao is None:
        print(
            "Nenhuma chave de LLM configurada. Defina GOOGLE_API_KEY (ou OPENAI_API_KEY) no arquivo .env "
            "local (copie de backend/.env.example) e rode o script novamente."
        )
        return 1

    resultados: List[Tuple[str, bool]] = [_executar("Chamada de texto", lambda: cliente_llm(PROMPT_TEXTO))]
    for nome_arquivo in AMOSTRAS_VISAO:
        resultados.append(
            _executar(f"Visão: {nome_arquivo}", _chamada_visao(cliente_visao, pasta_amostras / nome_arquivo))
        )

    falhas = [nome for nome, sucesso in resultados if not sucesso]
    print(f"Resumo: {len(resultados) - len(falhas)}/{len(resultados)} chamadas responderam.")
    return 1 if falhas else 0


def main() -> int:
    print(f"Provedor configurado: {descrever_provedor()}\n")
    return executar_testes(obter_cliente_llm(), obter_cliente_visao())


if __name__ == "__main__":
    sys.exit(main())
