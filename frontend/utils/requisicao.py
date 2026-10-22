from datetime import datetime

CANAIS_DE_ORIGEM = ["Pronto_Socorro", "Ambulatorio", "Laboratorio", "Operadora_de_Saude"]
EXTENSOES_ACEITAS = ["pdf", "png", "jpg", "jpeg", "txt", "json"]

TIPO_ARQUIVO_POR_EXTENSAO = {
    "pdf": "PDF",
    "png": "IMAGEM",
    "jpg": "IMAGEM",
    "jpeg": "IMAGEM",
    "txt": "TEXTO",
    "json": "JSON",
}


def montar_requisicao(arquivo, texto_digitado: str, canal_origem: str) -> dict:
    if arquivo is None:
        tipo_arquivo = "TEXTO"
        documento_texto = texto_digitado
    else:
        tipo_arquivo = _identificar_tipo_arquivo(arquivo.name)
        documento_texto = _extrair_texto(arquivo, tipo_arquivo)

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
        return arquivo.getvalue().decode("utf-8")
    except UnicodeDecodeError as erro:
        raise ValueError("O arquivo de texto precisa estar codificado em UTF-8.") from erro


def _gerar_documento_id() -> str:
    return f"DOC-CLIN-{datetime.now():%Y%m%d%H%M%S}"