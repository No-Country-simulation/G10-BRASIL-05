from services.cliente_http import requisitar
from services.erros import ErroDeApi

PREFIXO_DO_WHATSAPP = "/api/v1/webhook/evolution"
TAMANHO_MAXIMO_DO_DETALHE = 200


def obter_status() -> dict:
    return _chamar("GET", "/status-instancia")


def gerar_qrcode() -> dict:
    resposta = _chamar("POST", "/conectar")
    if resposta.get("conectado") or (resposta.get("sucesso") and resposta.get("base64")):
        return resposta
    raise ErroDeApi(_montar_mensagem("Não foi possível obter o QR Code.", resposta))


def configurar_webhook(url: str | None = None) -> dict:
    resposta = _chamar("POST", "/configurar-webhook", json={"url": url} if url else {})
    return _exigir_sucesso(resposta, "Não foi possível configurar o webhook.")


def desconectar() -> dict:
    resposta = _chamar("POST", "/desconectar")
    return _exigir_sucesso(resposta, "Não foi possível desconectar o WhatsApp.")


def enviar_mensagem_de_teste(numero: str, texto: str) -> dict:
    return _chamar("POST", "/enviar-teste", json={"numero": numero, "texto": texto})


def _chamar(metodo: str, caminho: str, **opcoes) -> dict:
    resposta = requisitar(metodo, f"{PREFIXO_DO_WHATSAPP}{caminho}", **opcoes)
    if not isinstance(resposta, dict):
        raise ErroDeApi("A API devolveu uma resposta inválida.")
    return resposta


def _exigir_sucesso(resposta: dict, mensagem: str) -> dict:
    # Alguns endpoints respondem HTTP 200 com {"sucesso": false}, o que também é falha
    if resposta.get("sucesso") is not True:
        raise ErroDeApi(_montar_mensagem(mensagem, resposta))
    return resposta


def _montar_mensagem(mensagem: str, resposta: dict) -> str:
    detalhe = str(resposta.get("erro") or resposta.get("resposta") or "sem detalhes")
    return f"{mensagem} Detalhe: {detalhe[:TAMANHO_MAXIMO_DO_DETALHE]}"
