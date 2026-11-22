"""Módulo de consulta de endereços por CEP (Código de Endereçamento Postal).

Utiliza o serviço público ViaCEP com controle de tempo limite e tratamento de exceções.
"""

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 5.0


def buscar_cep(cep: str) -> Optional[dict]:
    """Consulta os dados de endereço correspondentes a um CEP via API do ViaCEP.

    Args:
        cep: String contendo o CEP, com ou sem formatação (hífen, pontos).

    Returns:
        dict | None: Dicionário contendo os campos:
            {
                "cep": str,
                "logradouro": str,
                "complemento": str,
                "bairro": str,
                "localidade": str,
                "uf": str
            }
            ou None caso o CEP seja inválido, não encontrado ou ocorra erro de conexão/timeout.
    """
    if not cep or not isinstance(cep, str):
        return None

    # Remove qualquer caractere que não seja dígito numérico
    cep_limpo = re.sub(r"\D", "", cep)

    # O CEP brasileiro deve ter exatamente 8 dígitos
    if len(cep_limpo) != 8:
        return None

    url = f"https://viacep.com.br/ws/{cep_limpo}/json/"

    # Tenta usar httpx prioritariamente, com fallback para urllib
    try:
        try:
            import httpx

            with httpx.Client(timeout=TIMEOUT_SEGUNDOS) as client:
                response = client.get(url)
                if response.status_code != 200:
                    return None
                dados = response.json()
        except ImportError:
            import urllib.error
            import urllib.request

            req = urllib.request.Request(
                url, headers={"User-Agent": "MediFlow/1.0"}
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
                if resp.status != 200:
                    return None
                corpo = resp.read().decode("utf-8")
                dados = json.loads(corpo)

        # ViaCEP retorna {"erro": true} ou {"erro": "true"} quando não encontra o CEP
        if dados.get("erro") in (True, "true", "True"):
            return None

        return {
            "cep": dados.get("cep", ""),
            "logradouro": dados.get("logradouro", ""),
            "complemento": dados.get("complemento", ""),
            "bairro": dados.get("bairro", ""),
            "localidade": dados.get("localidade", ""),
            "uf": dados.get("uf", ""),
        }
    except Exception as exc:
        logger.warning("Falha ao consultar ViaCEP para o CEP %s: %s", cep_limpo, exc)
        return None
