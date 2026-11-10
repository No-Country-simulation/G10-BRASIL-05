from services import cliente_http, cliente_mock, cliente_whatsapp
from services.configuracao import usar_dados_simulados
from services.erros import ErroDeApi


def enviar_documento(requisicao: dict, arquivo=None) -> dict:
    return _cliente().enviar_documento(requisicao, arquivo)


def listar_documentos() -> list[dict]:
    return _cliente().listar_documentos()


def buscar_documento(documento_id: str) -> dict | None:
    return _cliente().buscar_documento(documento_id)


def listar_fila_auditoria() -> list[dict]:
    return _cliente().listar_fila_auditoria()


def registrar_decisao(documento_id: str, decisao: dict) -> dict:
    _exigir_api_real("registrar a decisão de auditoria")
    return cliente_http.registrar_decisao(documento_id, decisao)


def obter_status_whatsapp() -> dict:
    _exigir_api_real("consultar o status do WhatsApp")
    return cliente_whatsapp.obter_status()


def gerar_qrcode_whatsapp() -> dict:
    _exigir_api_real("gerar o QR Code do WhatsApp")
    return cliente_whatsapp.gerar_qrcode()


def configurar_webhook_whatsapp(url: str | None = None) -> dict:
    _exigir_api_real("configurar o webhook do WhatsApp")
    return cliente_whatsapp.configurar_webhook(url)


def desconectar_whatsapp() -> dict:
    _exigir_api_real("desconectar o WhatsApp")
    return cliente_whatsapp.desconectar()


def enviar_teste_whatsapp(numero: str, texto: str) -> dict:
    _exigir_api_real("enviar a mensagem de teste do WhatsApp")
    return cliente_whatsapp.enviar_mensagem_de_teste(numero, texto)


def _cliente():
    return cliente_mock if usar_dados_simulados() else cliente_http


def _exigir_api_real(acao: str) -> None:
    # Ações que gravam ou enviam algo nunca são simuladas: sem API real, falham
    if usar_dados_simulados():
        raise ErroDeApi(
            f"Não foi possível {acao}: o modo demonstração não usa a API real. "
            "Nada foi salvo nem enviado."
        )
