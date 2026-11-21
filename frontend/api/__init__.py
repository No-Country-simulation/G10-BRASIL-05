"""Fachada da comunicação do frontend com os serviços HTTP."""
from . import cliente_http, cliente_whatsapp


def enviar_documento(requisicao: dict, arquivo=None) -> dict:
    return cliente_http.enviar_documento(requisicao, arquivo)


def enfileirar_documento(requisicao: dict, arquivo) -> dict:
    return cliente_http.enfileirar_documento(requisicao, arquivo)


def enfileirar_documentos(arquivos: list, canal_origem: str = "Pronto_Socorro") -> dict:
    return cliente_http.enfileirar_documentos(arquivos, canal_origem)


def enfileirar_texto_documento(requisicao: dict) -> dict:
    return cliente_http.enfileirar_texto_documento(requisicao)


def obter_status_triagem(documento_id: str) -> dict:
    return cliente_http.obter_status_triagem(documento_id)


def inspecionar_extracao(requisicao: dict, arquivo=None) -> dict:
    return cliente_http.inspecionar_extracao(requisicao, arquivo)


def listar_documentos() -> list[dict]:
    return cliente_http.listar_documentos()


def listar_usuarios() -> list[dict]:
    return cliente_http.listar_usuarios()


def provisionar_usuario(dados: dict) -> dict:
    return cliente_http.provisionar_usuario(dados)


def atualizar_usuario(usuario_id: int, dados: dict) -> dict:
    return cliente_http.atualizar_usuario(usuario_id, dados)


def desativar_usuario(usuario_id: int) -> None:
    cliente_http.desativar_usuario(usuario_id)


def buscar_documento(documento_id: str) -> dict | None:
    return cliente_http.buscar_documento(documento_id)


def listar_fila_auditoria() -> list[dict]:
    return cliente_http.listar_fila_auditoria()


def obter_fonte_original(documento_id: str):
    return cliente_http.obter_fonte_original(documento_id)


def registrar_decisao(documento_id: str, decisao: dict) -> dict:
    return cliente_http.registrar_decisao(documento_id, decisao)


def obter_status_lock_auditoria(documento_id: str) -> dict:
    return cliente_http.obter_status_lock_auditoria(documento_id)


def bloquear_documento_auditoria(
    documento_id: str, auditor_nome: str, ttl_segundos: int = 300
) -> dict:
    return cliente_http.bloquear_documento_auditoria(documento_id, auditor_nome, ttl_segundos)


def desbloquear_documento_auditoria(documento_id: str, auditor_nome: str) -> dict:
    return cliente_http.desbloquear_documento_auditoria(documento_id, auditor_nome)


def obter_status_whatsapp() -> dict:
    return cliente_whatsapp.obter_status()


def gerar_qrcode_whatsapp() -> dict:
    return cliente_whatsapp.gerar_qrcode()


def configurar_webhook_whatsapp(url: str | None = None) -> dict:
    return cliente_whatsapp.configurar_webhook(url)


def desconectar_whatsapp() -> dict:
    return cliente_whatsapp.desconectar()


def enviar_teste_whatsapp(numero: str, texto: str) -> dict:
    return cliente_whatsapp.enviar_mensagem_de_teste(numero, texto)
