"""Estado e operações locais dos arquivos enviados para triagem."""
from dataclasses import dataclass, field
from uuid import uuid4

import streamlit as st

LIMITE_TAMANHO_BYTES = 10 * 1024 * 1024
CHAVE_ARQUIVOS = "triagem_arquivos"
CHAVE_VERSAO_UPLOADER = "triagem_versao_uploader"


@dataclass
class ArquivoCarregado:
    """Arquivo mantido na sessão; imita a interface do UploadedFile usada pelo cliente HTTP."""
    name: str
    size: int
    type: str
    dados: bytes = field(repr=False)
    id: str = field(default_factory=lambda: uuid4().hex)

    def getvalue(self) -> bytes:
        return self.dados

    @property
    def valido(self) -> bool:
        return self.size <= LIMITE_TAMANHO_BYTES


def formatar_tamanho(tamanho: int) -> str:
    if tamanho < 1024:
        return f"{tamanho} B"
    if tamanho < 1024 * 1024:
        return f"{tamanho / 1024:.1f} KB".replace(".", ",")
    return f"{tamanho / (1024 * 1024):.1f} MB".replace(".", ",")


def remover_arquivo(arquivo_id: str) -> None:
    st.session_state[CHAVE_ARQUIVOS] = [
        arquivo for arquivo in st.session_state[CHAVE_ARQUIVOS]
        if arquivo.id != arquivo_id
    ]
