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


def enfileirar_documento(requisicao: dict, arquivo) -> dict:
    tipo_de_conteudo = arquivo.type or _adivinhar_tipo_de_conteudo(arquivo.name)
    arquivos = {"file": (arquivo.name, arquivo.getvalue(), tipo_de_conteudo)}
    dados = {"canal_origem": requisicao["canal_origem"], "documento_id": requisicao["documento_id"]}
    return requisitar("POST", f"{PREFIXO_DA_TRIAGEM}/upload/enfileirar", files=arquivos, data=dados)


def enfileirar_documentos(arquivos_carregados: list, canal_origem: str = "Pronto_Socorro") -> dict:
    """Envia vários arquivos na mesma requisição multipart; a API devolve um ID por arquivo."""
    arquivos = [
        (
            "files",
            (arquivo.name, arquivo.getvalue(), arquivo.type or _adivinhar_tipo_de_conteudo(arquivo.name)),
        )
        for arquivo in arquivos_carregados
    ]
    return requisitar(
        "POST",
        f"{PREFIXO_DA_TRIAGEM}/upload/enfileirar",
        files=arquivos,
        data={"canal_origem": canal_origem},
    )


def enfileirar_texto_documento(requisicao: dict) -> dict:
    """Envia texto colado para acompanhamento por etapas, igual ao upload assíncrono."""
    return requisitar("POST", f"{PREFIXO_DA_TRIAGEM}/texto/enfileirar", json=requisicao)


def obter_status_triagem(documento_id: str) -> dict:
    return requisitar("GET", f"{PREFIXO_DA_TRIAGEM}/trabalhos/{documento_id}")


def inspecionar_extracao(requisicao: dict, arquivo=None) -> dict:
    dados = {
        "tipo_arquivo": requisicao["tipo_arquivo"],
        "documento_texto": requisicao["documento_texto"],
    }
    arquivos = None
    if arquivo is not None and requisicao["tipo_arquivo"] in TIPOS_COM_UPLOAD:
        tipo_de_conteudo = arquivo.type or _adivinhar_tipo_de_conteudo(arquivo.name)
        arquivos = {"file": (arquivo.name, arquivo.getvalue(), tipo_de_conteudo)}
        dados.pop("documento_texto")
    return requisitar("POST", f"{PREFIXO_DA_TRIAGEM}/inspecionar", files=arquivos, data=dados)


def listar_documentos() -> list[dict]:
    try:
        docs = requisitar("GET", f"{PREFIXO_DA_TRIAGEM}/documentos")
        if docs:
            return docs
    except Exception:
        pass
    from data.dados_mock import obter_mocks_listagem
    return obter_mocks_listagem()


def listar_usuarios() -> list[dict]:
    return requisitar("GET", "/api/v1/auth/usuarios")


def provisionar_usuario(dados: dict) -> dict:
    return requisitar("POST", "/api/v1/auth/usuarios", json=dados)


def atualizar_usuario(usuario_id: int, dados: dict) -> dict:
    return requisitar("PATCH", f"/api/v1/auth/usuarios/{usuario_id}", json=dados)


def desativar_usuario(usuario_id: int) -> None:
    caminho = f"/api/v1/auth/usuarios/{usuario_id}"
    try:
        with _criar_cliente() as cliente:
            resposta = cliente.delete(caminho)
    except httpx.TimeoutException as erro:
        raise ErroDeApi("A API demorou demais para responder. Tente novamente.") from erro
    except httpx.HTTPError as erro:
        raise ErroDeApi("Não foi possível conectar à API. Verifique se ela está em execução.") from erro
    if resposta.is_error:
        raise ErroDeApi(_extrair_mensagem_de_erro(resposta))


def buscar_documento(documento_id: str) -> dict | None:
    try:
        detalhe = requisitar("GET", f"{PREFIXO_DA_TRIAGEM}/documentos/{documento_id}")
        if detalhe:
            return detalhe
    except Exception:
        pass
    from data.dados_mock import obter_mock_documento_detalhado
    return obter_mock_documento_detalhado(documento_id)


def listar_fila_auditoria() -> list[dict]:
    try:
        fila = requisitar("GET", f"{PREFIXO_DA_TRIAGEM}/auditoria")
        if fila:
            return fila
    except Exception:
        pass
    from data.dados_mock import obter_mocks_auditoria
    return obter_mocks_auditoria()


def registrar_decisao(documento_id: str, decisao: dict) -> dict:
    return requisitar("POST", f"{PREFIXO_DA_TRIAGEM}/auditoria/{documento_id}/decisao", json=decisao)


def obter_status_lock_auditoria(documento_id: str) -> dict:
    return requisitar("GET", f"{PREFIXO_DA_TRIAGEM}/auditoria/{documento_id}/status-lock")


def bloquear_documento_auditoria(documento_id: str, auditor_nome: str, ttl_segundos: int = 300) -> dict:
    return requisitar(
        "POST",
        f"{PREFIXO_DA_TRIAGEM}/auditoria/{documento_id}/bloquear",
        json={"auditor_nome": auditor_nome, "ttl_segundos": ttl_segundos},
    )


def desbloquear_documento_auditoria(documento_id: str, auditor_nome: str) -> dict:
    return requisitar(
        "POST",
        f"{PREFIXO_DA_TRIAGEM}/auditoria/{documento_id}/desbloquear",
        json={"auditor_nome": auditor_nome},
    )


def obter_fonte_original(documento_id: str) -> tuple[bytes, str, str]:
    caminhos = [
        f"{PREFIXO_DA_TRIAGEM}/documentos/{documento_id}/fonte",
        f"{PREFIXO_DA_TRIAGEM}/auditoria/{documento_id}/fonte",
    ]
    for caminho in caminhos:
        try:
            with _criar_cliente() as cliente:
                resposta = cliente.get(caminho)
                if not resposta.is_error:
                    nome = resposta.headers.get("content-disposition", "").split("filename=")[-1].strip('"')
                    return resposta.content, resposta.headers.get("content-type", "application/octet-stream"), nome
        except Exception:
            pass

    from data.dados_mock import obter_mock_documento_detalhado
    mock_doc = obter_mock_documento_detalhado(documento_id)
    if mock_doc:
        texto = mock_doc.get("texto_extraido") or f"Documento de triagem - Protocolo {documento_id}"
        return texto.encode("utf-8"), "text/plain", f"{documento_id}_transcricao.txt"

    raise ErroDeApi("Documento original indisponível no momento.")


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


def _obter_headers_autenticacao() -> dict[str, str]:
    try:
        import streamlit as st
        from services.autenticacao import obter_cabecalho_autorizacao

        return obter_cabecalho_autorizacao(st.session_state)
    except Exception:
        return {}


def _criar_cliente() -> httpx.Client:
    headers = _obter_headers_autenticacao()
    return httpx.Client(
        base_url=obter_url_do_backend(),
        timeout=obter_tempo_limite_em_segundos(),
        headers=headers if headers else None,
    )


def _extrair_mensagem_de_erro(resposta: httpx.Response) -> str:
    mensagem_padrao = f"A API respondeu com erro {resposta.status_code}."
    try:
        payload = resposta.json()
    except ValueError:
        return mensagem_padrao
    detalhe = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detalhe, str) and detalhe.strip():
        return detalhe
    try:
        erro = payload["erro"]
        mensagem = erro["mensagem"]
    except (ValueError, KeyError, TypeError):
        return mensagem_padrao
    detalhes = [
        f"{detalhe.get('campo')}: {detalhe.get('motivo')}"
        for detalhe in erro.get("detalhes") or []
        if isinstance(detalhe, dict)
    ]
    return f"{mensagem} ({'; '.join(detalhes)})" if detalhes else mensagem
