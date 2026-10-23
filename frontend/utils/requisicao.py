from datetime import datetime

CANAIS_DE_ORIGEM = ["Pronto_Socorro", "Ambulatorio", "Laboratorio", "Operadora_de_Saude"]
EXTENSOES_ACEITAS = ["pdf", "png", "jpg", "jpeg", "txt", "json"]

OPCAO_ARQUIVO = "Enviar arquivo"
OPCAO_TEXTO = "Colar texto"

TIPO_ARQUIVO_POR_EXTENSAO = {
    "pdf": "PDF",
    "png": "IMAGEM",
    "jpg": "IMAGEM",
    "jpeg": "IMAGEM",
    "txt": "TEXTO",
    "json": "JSON",
}


def validar_envio(fonte: str, arquivo, texto_digitado: str, canal_origem: str | None) -> str | None:
    if fonte == OPCAO_ARQUIVO and arquivo is None:
        return "Selecione um arquivo para analisar."
    if fonte == OPCAO_TEXTO and not texto_digitado.strip():
        return "Cole o texto do documento para analisar."
    if canal_origem is None:
        return "Selecione o canal de origem do documento."
    return None


def montar_requisicao(arquivo, texto_digitado: str, canal_origem: str) -> dict:
    if arquivo is None:
        tipo_arquivo = "TEXTO"
        documento_texto = texto_digitado
    else:
        tipo_arquivo = _identificar_tipo_arquivo(arquivo.name)
        documento_texto = _extrair_texto(arquivo, tipo_arquivo)

    if not documento_texto.strip():
        raise ValueError("O documento está vazio.")

    return {
        "documento_id": _gerar_documento_id(),
        "tipo_arquivo": tipo_arquivo,
        "documento_texto": documento_texto,
        "canal_origem": canal_origem,
    }


def _identificar_tipo_arquivo(nome_arquivo: str) -> str:
    extensao = nome_arquivo.rsplit(".", 1)[-1].lower()
    return TIPO_ARQUIVO_POR_EXTENSAO[extensao]


def _extrair_texto(arquivo, tipo_arquivo: str) -> str:
    if tipo_arquivo not in ("TEXTO", "JSON"):
        return arquivo.name
    try:
        return arquivo.getvalue().decode("utf-8-sig")
    except UnicodeDecodeError as erro:
        raise ValueError("O arquivo de texto precisa estar codificado em UTF-8.") from erro


def _gerar_documento_id() -> str:
    return f"DOC-CLIN-{datetime.now():%Y%m%d%H%M%S}"