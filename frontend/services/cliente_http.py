import mimetypes

import httpx

from services.configuracao import (
    obter_tempo_limite_em_segundos,
    obter_url_do_backend,
)
from services.erros import ErroDeApi

PREFIXO_DA_TRIAGEM = "/api/v1/triagem"
TIPOS_COM_UPLOAD = ("PDF", "IMAGEM")
TIPO_DE_CONTEUDO_PADRAO = "application/octet-stream"


def enviar_documento(requisicao: dict, arquivo=None) -> dict:
    if arquivo is not None and requisicao["tipo_arquivo"] in TIPOS_COM_UPLOAD:
        return _enviar_arquivo(requisicao, arquivo)
    return requisitar("POST", PREFIXO_DA_TRIAGEM, json=requisicao)


def listar_documentos() -> list[dict]:
    return requisitar("GET", f"{PREFIXO_DA_TRIAGEM}/documentos")


def buscar_documento(documento_id: str) -> dict | None:
    # O backend ainda não tem endpoint de detalhe do documento (SCRUM-68)
    return None


def listar_fila_auditoria() -> list[dict]:
    return requisitar("GET", f"{PREFIXO_DA_TRIAGEM}/auditoria")


def registrar_decisao(documento_id: str, decisao: dict) -> dict:
    return requisitar("POST", f"{PREFIXO_DA_TRIAGEM}/auditoria/{documento_id}/decisao", json=decisao)


def _enviar_arquivo(requisicao: dict, arquivo) -> dict:
    tipo_de_conteudo = arquivo.type or _adivinhar_tipo_de_conteudo(arquivo.name)
    arquivos = {"file": (arquivo.name, arquivo.getvalue(), tipo_de_conteudo)}
    dados = {"canal_origem": requisicao["canal_origem"], "documento_id": requisicao["documento_id"]}
    return requisitar("POST", f"{PREFIXO_DA_TRIAGEM}/upload", files=arquivos, data=dados)


def _adivinhar_tipo_de_conteudo(nome_do_arquivo: str) -> str:
    # O backend recusa application/octet-stream, então o tipo vem da extensão
    return mimetypes.guess_type(nome_do_arquivo)[0] or TIPO_DE_CONTEUDO_PADRAO


def requisitar(metodo: str, caminho: str, **opcoes):
    try:
        with _criar_cliente() as cliente:
            resposta = cliente.request(metodo, caminho, **opcoes)
    except httpx.TimeoutException as erro:
        raise ErroDeApi("A API demorou demais para responder. Tente novamente.") from erro
    except httpx.HTTPError as erro:
        raise ErroDeApi("Não foi possível conectar à API. Verifique se ela está em execução.") from erro
    if resposta.is_error:
        raise ErroDeApi(_extrair_mensagem_de_erro(resposta))
    try:
        return resposta.json()
    except ValueError as erro:
        raise ErroDeApi("A API devolveu uma resposta inválida.") from erro


def _criar_cliente() -> httpx.Client:
    return httpx.Client(base_url=obter_url_do_backend(), timeout=obter_tempo_limite_em_segundos())


def _extrair_mensagem_de_erro(resposta: httpx.Response) -> str:
    mensagem_padrao = f"A API respondeu com erro {resposta.status_code}."
    try:
        erro = resposta.json()["erro"]
        mensagem = erro["mensagem"]
    except (ValueError, KeyError, TypeError):
        return mensagem_padrao
    detalhes = [
        f"{detalhe.get('campo')}: {detalhe.get('motivo')}"
        for detalhe in erro.get("detalhes") or []
        if isinstance(detalhe, dict)
    ]
    return f"{mensagem} ({'; '.join(detalhes)})" if detalhes else mensagem
