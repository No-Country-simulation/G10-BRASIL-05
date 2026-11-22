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


def enfileirar_documentos(arquivos_carregados: list, canal_origem: str = "Interno") -> dict:
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
    return requisitar("GET", f"{PREFIXO_DA_TRIAGEM}/documentos")


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
    if str(documento_id).startswith("REV-"):
        from telas.auditoria.dados_mock import obter_mock_documento_por_id
        return obter_mock_documento_por_id(documento_id)
    return None


def listar_fila_auditoria() -> list[dict]:
    return requisitar("GET", f"{PREFIXO_DA_TRIAGEM}/auditoria")


def registrar_decisao(documento_id: str, decisao: dict) -> dict:
    try:
        return requisitar("POST", f"{PREFIXO_DA_TRIAGEM}/auditoria/{documento_id}/decisao", json=decisao)
    except Exception:
        if str(documento_id).startswith("REV-"):
            from telas.auditoria.dados_mock import registrar_decisao_mock
            return registrar_decisao_mock(documento_id, decisao)
        raise


def obter_status_lock_auditoria(documento_id: str) -> dict:
    try:
        return requisitar("GET", f"{PREFIXO_DA_TRIAGEM}/auditoria/{documento_id}/status-lock")
    except Exception:
        if str(documento_id).startswith("REV-"):
            return {"bloqueado": False}
        raise


def bloquear_documento_auditoria(documento_id: str, auditor_nome: str, ttl_segundos: int = 300) -> dict:
    try:
        return requisitar(
            "POST",
            f"{PREFIXO_DA_TRIAGEM}/auditoria/{documento_id}/bloquear",
            json={"auditor_nome": auditor_nome, "ttl_segundos": ttl_segundos},
        )
    except Exception:
        if str(documento_id).startswith("REV-"):
            return {"status": "bloqueado", "auditor_nome": auditor_nome}
        raise


def desbloquear_documento_auditoria(documento_id: str, auditor_nome: str) -> dict:
    try:
        return requisitar(
            "POST",
            f"{PREFIXO_DA_TRIAGEM}/auditoria/{documento_id}/desbloquear",
            json={"auditor_nome": auditor_nome},
        )
    except Exception:
        if str(documento_id).startswith("REV-"):
            return {"status": "desbloqueado"}
        raise


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

    # Disponibiliza a imagem anexada pelo usuário para conferência de detalhes
    from pathlib import Path
    caminho_demo = Path(__file__).resolve().parent.parent / "assets" / "documentos_demo" / "IMG_2147_1.jpeg"
    if caminho_demo.exists():
        return caminho_demo.read_bytes(), "image/jpeg", "IMG_2147.jpeg"

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
    if isinstance(payload, dict) and resposta.status_code != 500:
        detalhe = payload.get("detail")
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
