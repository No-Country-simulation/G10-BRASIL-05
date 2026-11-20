"""Templates e versionamento de prompts para ingestão e extração de entidades com LLMs (SCRUM-64).

Cada módulo de prompt declara:
- `VERSAO`: versão semântica do prompt, registrada na saída do nó que o usa.
- `EXEMPLOS`: pares (documento, resposta esperada) incluídos no prompt de sistema
  e validados pelos testes contra o schema Pydantic do nó.

Toda alteração de texto, regra ou exemplo exige incrementar `VERSAO` e registrar a
mudança em `CHANGELOG.md`, nesta mesma pasta.
"""

import json
from typing import Any, Dict, List, Tuple

ExemploPrompt = Tuple[str, Dict[str, Any]]


def formatar_exemplos(exemplos: List[ExemploPrompt]) -> str:
    """Formata os exemplos few-shot para anexar ao prompt de sistema."""
    blocos = [
        f"Exemplo {indice}:\nDocumento:\n\"\"\"\n{documento}\n\"\"\"\nResposta:\n{json.dumps(resposta, ensure_ascii=False)}"
        for indice, (documento, resposta) in enumerate(exemplos, start=1)
    ]
    return "\n\n".join(blocos)
