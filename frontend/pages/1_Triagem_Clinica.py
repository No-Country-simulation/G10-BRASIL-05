from dataclasses import dataclass, field
from html import escape
import time
from uuid import uuid4

import streamlit as st

from components.cards import exibir_resultado_da_triagem
from services.api_client import (
    enfileirar_documentos,
    enfileirar_texto_documento,
    obter_status_triagem,
)
from services.erros import ErroDeApi
from utils.requisicao import (
    EXTENSOES_ACEITAS,
    OPCAO_ARQUIVO,
    OPCAO_TEXTO,
    montar_requisicao,
)

LIMITE_TAMANHO_BYTES = 10 * 1024 * 1024  # 10 MB, mesmo limite do backend
CHAVE_ARQUIVOS = "triagem_arquivos"
CHAVE_VERSAO_UPLOADER = "triagem_versao_uploader"
FORMATOS_TEXTO = "PDF, PNG, JPG, WEBP, HEIC, TXT ou JSON"


def _mostrar_andamento_trabalho(slot, nome: str, estado: dict) -> None:
    etapas = {
        "leitura_documento": "lendo o documento",
        "identificacao": "identificando paciente e médico",
        "analise_clinica": "analisando o conteúdo clínico",
    }
    etapa = etapas.get(estado.get("etapa_atual"), "em processamento")
    parcial = estado.get("resultado_parcial")
    slot.empty()
    slot.info(f"{nome}: {etapa}")
    if not parcial:
        return

    status_cadastro = {
        "encontrado": "correspondência encontrada",
        "nao_encontrado": "não localizado no cadastro",
        "ambiguo": "mais de uma correspondência possível",
        "dados_insuficientes": "dados insuficientes para buscar",
        "crm_ausente": "CRM não identificado no documento",
    }
    for entidade in ("Paciente", "Médico solicitante"):
        dados = parcial.get(entidade) or {}
        documento = dados.get("dados_documento") or {}
        cadastro = dados.get("cadastro") or {}
        nome_documento = documento.get("nome") or "não identificado"
        estado_cadastro = status_cadastro.get(
            dados.get("status"), "situação cadastral não confirmada"
        )
        detalhes = f"{entidade}: {nome_documento} · {estado_cadastro}"
        nome_cadastro = cadastro.get("nome")
        if nome_cadastro and nome_cadastro != nome_documento:
            detalhes += f" · Cadastro: {nome_cadastro}"
        if cadastro.get("cadastro_provisorio"):
            detalhes += " · Cadastro provisório"
        crm = documento.get("crm") or cadastro.get("crm")
        idade = documento.get("idade")
        if entidade == "Paciente" and idade is not None:
            detalhes += f" · {idade} anos no documento"
        if entidade == "Médico solicitante" and crm:
            detalhes += f" · CRM {crm}"
        especialidade = cadastro.get("especialidade")
        if entidade == "Médico solicitante" and especialidade:
            detalhes += f" · {especialidade}"
        slot.text(detalhes)
    slot.caption("A análise clínica continua automaticamente.")


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


def _remover_arquivo(arquivo_id: str) -> None:
    st.session_state[CHAVE_ARQUIVOS] = [
        a for a in st.session_state[CHAVE_ARQUIVOS] if a.id != arquivo_id
    ]


ICONE_UPLOAD = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
    "stroke='%230B3C7A' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E"
    "%3Cpath d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/%3E%3Cpolyline points='17 8 12 3 7 8'/%3E"
    "%3Cline x1='12' y1='3' x2='12' y2='15'/%3E%3C/svg%3E\")"
)

CSS = """
<style>
[data-testid="stMain"] { background: #F5F9FC !important; }
[data-testid="stMainBlockContainer"] { max-width: 1060px !important; }

/* Cabeçalho */
[data-testid="stMain"] h1 {
    color: #0B2A5B !important; font-size: 2rem !important; font-weight: 800 !important;
    letter-spacing: -0.02em !important; padding: 0 !important; margin: 0 !important;
}
.triagem-subtitulo { color: #334155; font-size: 0.86rem; margin: 4px 0 10px 0; }

/* Card principal */
.st-key-triagem_card {
    background: #FFFFFF !important; border: 1px solid #E3ECF3 !important;
    border-radius: 14px !important; padding: 22px 22px 18px 22px !important;
}

/* Alternador Enviar arquivo / Colar texto */
.st-key-triagem_fonte [data-testid="stButtonGroup"] > div,
.st-key-triagem_fonte [role="radiogroup"],
.st-key-triagem_fonte [data-baseweb="button-group"] {
    background: #E6F2F9 !important; border-radius: 999px !important; padding: 3px !important;
    gap: 0 !important; display: inline-flex !important; width: auto !important;
}
.st-key-triagem_fonte button {
    background: transparent !important; border: none !important; box-shadow: none !important;
    border-radius: 999px !important; padding: 6px 16px !important; min-height: 30px !important;
    color: #0B2A5B !important;
}
.st-key-triagem_fonte button p { font-size: 0.78rem !important; font-weight: 600 !important; }
.st-key-triagem_fonte button[data-testid="stBaseButton-segmented_controlActive"],
.st-key-triagem_fonte button[kind="segmented_controlActive"],
.st-key-triagem_fonte button[aria-checked="true"] {
    background: #0B3C7A !important; color: #FFFFFF !important;
}
.st-key-triagem_fonte button[data-testid="stBaseButton-segmented_controlActive"] p,
.st-key-triagem_fonte button[kind="segmented_controlActive"] p,
.st-key-triagem_fonte button[aria-checked="true"] p { color: #FFFFFF !important; }

/* Botão Analisar */
.st-key-triagem_acao button {
    width: 100% !important; border-radius: 999px !important; min-height: 38px !important;
    background: #0B3C7A !important; border: none !important; color: #FFFFFF !important;
}
.st-key-triagem_acao button p { font-size: 0.86rem !important; font-weight: 700 !important; }
.st-key-triagem_acao button:disabled { background: #D9E2EA !important; color: #64748B !important; }
.st-key-triagem_acao button:disabled p { color: #64748B !important; }
.triagem-aviso { color: #475569; font-size: 0.7rem; line-height: 1.35; margin-top: -4px; }

/* ===== Dropzone (comum) ===== */
.st-key-triagem_drop [data-testid="stFileUploader"] { margin: 0 !important; }
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"]:not(:has([data-testid="stFileChipName"])) {
    background: #EEF6FC !important; border: 1.5px dashed #8DBAD6 !important;
    border-radius: 12px !important; display: flex !important; align-items: center !important;
    cursor: pointer !important;
}
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"]:not(:has([data-testid="stFileChipName"])):hover { border-color: #0B3C7A !important; }
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"]:not(:has([data-testid="stFileChipName"]))::before {
    content: ""; order: 0; flex-shrink: 0; background: ICONE center / contain no-repeat;
}
.st-key-triagem_drop [data-testid="stFileUploaderDropzoneInstructions"] { order: 1; margin: 0 !important; }
.st-key-triagem_drop [data-testid="stFileUploaderDropzoneInstructions"] * { display: none !important; }
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"] > div:has(button) { order: 2; margin: 0 !important; }

/* Botão principal de seleção / adição de arquivos (NUNCA os botões internos de chip) */
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"] > span > button,
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileChips"]) button,
.st-key-triagem_drop [data-testid="stFileChips"] > button {
    background: #FFFFFF !important; border: 1.5px solid #0B3C7A !important; border-radius: 999px !important;
    color: #0B3C7A !important; padding: 6px 18px !important; min-height: 0 !important; cursor: pointer !important;
}
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"] > span > button > *,
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileChips"]) button > *,
.st-key-triagem_drop [data-testid="stFileChips"] > button > * { display: none !important; }
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"] > span > button::after,
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileChips"]) button::after,
.st-key-triagem_drop [data-testid="stFileChips"] > button::after {
    font-size: 0.78rem; font-weight: 700; color: #0B3C7A;
}

/* ===== Dropzone vazia (grande) ===== */
.st-key-triagem_drop_vazia [data-testid="stFileUploaderDropzone"]:not(:has([data-testid="stFileChipName"])) {
    flex-direction: column !important; justify-content: center !important;
    padding: 30px 16px 26px 16px !important; gap: 6px !important; text-align: center !important;
}
.st-key-triagem_drop_vazia [data-testid="stFileUploaderDropzone"]:not(:has([data-testid="stFileChipName"]))::before { width: 26px; height: 26px; margin-bottom: 4px; }
.st-key-triagem_drop_vazia [data-testid="stFileUploaderDropzoneInstructions"] {
    display: flex !important; flex-direction: column !important; align-items: center !important; gap: 4px;
}
.st-key-triagem_drop_vazia [data-testid="stFileUploaderDropzoneInstructions"]::before {
    content: "Arraste o documento aqui"; font-size: 0.86rem; font-weight: 700; color: #0B2A5B;
}
.st-key-triagem_drop_vazia [data-testid="stFileUploaderDropzoneInstructions"]::after {
    content: "ou"; font-size: 0.7rem; color: #475569;
}
.st-key-triagem_drop_vazia [data-testid="stFileUploaderDropzone"] > span > button::after,
.st-key-triagem_drop_vazia [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileChips"]) button::after {
    content: "Selecionar arquivo";
}
.st-key-triagem_drop_vazia [data-testid="stFileUploaderDropzone"]::after {
    content: "FORMATOS · até 10 MB por arquivo"; order: 3; font-size: 0.66rem; color: #475569; margin-top: 4px;
}

/* ===== Dropzone compacta (com arquivos) ===== */
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzone"]:not(:has([data-testid="stFileChipName"])) {
    flex-direction: row !important; flex-wrap: wrap !important; padding: 12px 18px !important; gap: 14px !important;
    min-height: 52px !important; max-height: 52px !important; box-sizing: border-box !important; width: 100% !important;
}
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzone"]:not(:has([data-testid="stFileChipName"]))::before { width: 22px; height: 22px; flex: 0 0 auto !important; }
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzoneInstructions"] {
    flex: 1 1 auto !important; text-align: left !important; display: block !important;
    font-size: 0.74rem; color: #334155; line-height: 1.35;
}
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzoneInstructions"]::before {
    content: "Arraste mais arquivos aqui"; font-weight: 700; color: #0B2A5B;
}
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzoneInstructions"]::after {
    content: " ou use o botão ao lado";
}
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzone"] > span > button,
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileChips"]) button {
    flex: 0 0 auto !important; margin-left: auto !important;
}
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzone"] > span > button::after,
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileChips"]) button::after,
.st-key-triagem_drop_compacta [data-testid="stFileChips"] > button::after {
    content: "Adicionar arquivos";
}

/* ===== Quando arquivos estão carregando (Streamlit monta stFileChips com nome):
   Remove qualquer contêiner externo/borda ao redor do dropzone, deixando a barra pontilhada
   no topo (52px) e os arquivos descendo para a lista abaixo exatamente como os selecionados ===== */
.st-key-triagem_drop [data-testid="stFileUploader"],
.st-key-triagem_drop_compacta [data-testid="stFileUploader"],
.st-key-triagem_drop_vazia [data-testid="stFileUploader"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    width: 100% !important;
}

[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]),
[data-testid="stFileUploader"]:has([data-testid="stFileChipName"]) [data-testid="stFileUploaderDropzone"],
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]),
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]),
.st-key-triagem_drop_vazia [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]) {
    background: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 0 !important;
    position: relative !important;
    min-height: 0 !important;
    max-height: none !important;
    width: 100% !important;
}

[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]):hover,
[data-testid="stFileUploader"]:has([data-testid="stFileChipName"]) [data-testid="stFileUploaderDropzone"]:hover,
.st-key-triagem_drop [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]):hover,
.st-key-triagem_drop_compacta [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]):hover,
.st-key-triagem_drop_vazia [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]):hover {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

/* Barra compacta pontilhada independente no topo */
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"])::before,
[data-testid="stFileUploader"]:has([data-testid="stFileChipName"]) [data-testid="stFileUploaderDropzone"]::before {
    content: "Arraste mais arquivos aqui ou use o botão ao lado" !important;
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    min-height: 52px !important;
    max-height: 52px !important;
    background-color: #EEF6FC !important;
    background-image: ICONE !important;
    background-position: 18px center !important;
    background-size: 22px 22px !important;
    background-repeat: no-repeat !important;
    border: 1.5px dashed #8DBAD6 !important;
    border-radius: 12px !important;
    padding: 12px 170px 12px 52px !important;
    box-sizing: border-box !important;
    font-size: 0.74rem !important;
    font-weight: 700 !important;
    color: #0B2A5B !important;
    cursor: pointer !important;
    flex: 0 0 52px !important;
}
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]):hover::before,
[data-testid="stFileUploader"]:has([data-testid="stFileChipName"]) [data-testid="stFileUploaderDropzone"]:hover::before {
    border-color: #0B3C7A !important;
}

/* Botão "Adicionar arquivos" fixo na barra compacta */
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"])::after,
[data-testid="stFileUploader"]:has([data-testid="stFileChipName"]) [data-testid="stFileUploaderDropzone"]::after {
    content: "Adicionar arquivos" !important;
    position: absolute !important;
    top: 10px !important;
    right: 14px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: #FFFFFF !important;
    border: 1.5px solid #0B3C7A !important;
    border-radius: 999px !important;
    color: #0B3C7A !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    padding: 6px 18px !important;
    height: 32px !important;
    box-sizing: border-box !important;
    pointer-events: none !important;
    z-index: 2 !important;
}

/* Oculta textos e botões nativos que conflitam */
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]) [data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploader"]:has([data-testid="stFileChipName"]) [data-testid="stFileUploaderDropzoneInstructions"] {
    display: none !important;
}
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChipName"]) button:not([data-testid*="stFileChipDeleteBtn"] button),
[data-testid="stFileUploader"]:has([data-testid="stFileChipName"]) button:not([data-testid*="stFileChipDeleteBtn"] button),
[data-testid="stFileChips"] > button {
    display: none !important;
}

/* Contêiner da lista de arquivos em carregamento */
[data-testid="stFileChips"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    width: 100% !important;
    min-width: 100% !important;
    box-sizing: border-box !important;
    gap: 8px !important;
    margin: 0 !important;
}
[data-testid="stFileChips"] > div {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    width: 100% !important;
    gap: 8px !important;
}

/* Título de resumo ÚNICO acima dos cards em carregamento (apenas quando de fato há arquivo) */
[data-testid="stFileChips"]:has([data-testid="stFileChipName"])::before {
    content: "Arquivos selecionados · até 10 MB cada" !important;
    display: block !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    color: #0B2A5B !important;
    margin: 12px 0 6px 0 !important;
    width: 100% !important;
}
.st-key-triagem_card:has([data-testid="stFileChipName"]) .triagem-contagem {
    display: none !important;
}

/* Card do arquivo que está sendo carregado (idêntico ao .arq-linha) */
[data-testid="stFileChip"] {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    flex: 1 1 100% !important;
    flex-basis: 100% !important;
    background: #FFFFFF !important;
    border: 1px solid #E3ECF3 !important;
    border-radius: 10px !important;
    padding: 10px 12px !important;
    box-sizing: border-box !important;
    gap: 12px !important;
    margin: 0 0 8px 0 !important;
}
[data-testid="stFileChip"] > div:first-child {
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    max-width: 36px !important;
    border-radius: 6px !important;
    background: #E8F3FA !important;
    border: 1px solid #CFE3F1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #0B3C7A !important;
    flex-shrink: 0 !important;
}
[data-testid="stFileChip"] > div:nth-child(2) {
    flex: 1 !important;
    min-width: 0 !important;
    display: grid !important;
    grid-template-columns: 1fr auto !important;
    grid-template-areas:
        "nome tamanho"
        "barra barra"
        "status status" !important;
    row-gap: 3px !important;
    column-gap: 8px !important;
    align-items: center !important;
}
[data-testid="stFileChip"] [data-testid="stFileChipName"] {
    grid-area: nome !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    color: #0B2A5B !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.2 !important;
}
[data-testid="stFileChip"] > div:nth-child(2) > div:last-child {
    grid-area: tamanho !important;
    font-size: 0.7rem !important;
    color: #334155 !important;
    white-space: nowrap !important;
    text-align: right !important;
    line-height: 1.2 !important;
}
[data-testid="stFileChip"] > div:nth-child(2)::before {
    content: "" !important;
    grid-area: barra !important;
    display: block !important;
    height: 4px !important;
    width: 100% !important;
    border-radius: 4px !important;
    background: #0B3C7A !important;
    margin: 2px 0 1px 0 !important;
}
[data-testid="stFileChip"] > div:nth-child(2)::after {
    content: "Enviando..." !important;
    grid-area: status !important;
    display: block !important;
    font-size: 0.68rem !important;
    color: #0B3C7A !important;
    font-weight: 500 !important;
    line-height: 1.2 !important;
}
[data-testid="stFileChipDeleteBtn"] {
    align-self: center !important;
    margin-left: auto !important;
    flex-shrink: 0 !important;
}
[data-testid="stFileChipDeleteBtn"] button {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 999px !important;
    min-height: 30px !important;
    padding: 4px 14px !important;
    color: #0B2A5B !important;
    cursor: pointer !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stFileChipDeleteBtn"] button:hover {
    border-color: #0B3C7A !important;
}
[data-testid="stFileChipDeleteBtn"] button > * {
    display: none !important;
}
[data-testid="stFileChipDeleteBtn"] button::after {
    content: "Cancelar" !important;
    font-size: 0.74rem !important;
    font-weight: 500 !important;
    color: #0B2A5B !important;
}

/* Linha de contagem */
.triagem-contagem {
    display: flex; justify-content: space-between; align-items: center; gap: 12px;
    margin: 2px 0 -2px 0; font-size: 0.68rem; color: #475569;
}
.triagem-contagem strong { color: #0B2A5B; font-size: 0.74rem; }

/* Cards de arquivo */
[class*="st-key-triagem_arq_"] {
    display: block !important; width: 100% !important; box-sizing: border-box !important;
    background: #FFFFFF !important; border: 1px solid #E3ECF3 !important;
    border-radius: 10px !important; padding: 10px 12px !important; margin-bottom: 8px !important;
}
[class*="st-key-triagem_arq_"] button {
    background: #FFFFFF !important; border: 1px solid #CBD5E1 !important; border-radius: 999px !important;
    min-height: 30px !important; padding: 4px 14px !important; color: #0B2A5B !important;
}
[class*="st-key-triagem_arq_"] button p { font-size: 0.74rem !important; font-weight: 500 !important; }
[class*="st-key-triagem_arq_"] button:hover { border-color: #0B3C7A !important; }
.arq-linha { display: flex; align-items: center; gap: 12px; }
.arq-badge {
    width: 36px; height: 36px; min-width: 36px; border-radius: 6px; background: #E8F3FA;
    border: 1px solid #CFE3F1; color: #0B3C7A; font-size: 0.6rem; font-weight: 800;
    display: flex; align-items: center; justify-content: center;
}
.arq-info { flex: 1; min-width: 0; }
.arq-topo { display: flex; justify-content: space-between; gap: 8px; }
.arq-nome { font-size: 0.78rem; font-weight: 700; color: #0B2A5B; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.arq-tamanho { font-size: 0.7rem; color: #334155; white-space: nowrap; }
.arq-barra { height: 4px; border-radius: 4px; margin: 4px 0 3px 0; }
.arq-status { font-size: 0.68rem; }

/* Colar texto */
.st-key-triagem_texto textarea {
    background: #EEF6FC !important; border-radius: 12px !important; font-size: 0.85rem !important;
}
</style>
""".replace("ICONE", ICONE_UPLOAD).replace("FORMATOS", FORMATOS_TEXTO)

st.html(CSS)

st.session_state.setdefault(CHAVE_ARQUIVOS, [])
st.session_state.setdefault(CHAVE_VERSAO_UPLOADER, 0)

st.title("Triagem Clínica")
st.html('<div class="triagem-subtitulo">Envie um documento clínico para análise e roteamento automático.</div>')

arquivos: list[ArquivoCarregado] = st.session_state[CHAVE_ARQUIVOS]
texto_digitado = ""

with st.container(key="triagem_card"):
    col_esquerda, col_direita = st.columns([1.55, 1], gap="large")

    with col_esquerda:
        with st.container(key="triagem_fonte"):
            fonte = st.segmented_control(
                "Como deseja enviar o documento?",
                [OPCAO_ARQUIVO, OPCAO_TEXTO],
                default=OPCAO_ARQUIVO,
                required=True,
                label_visibility="collapsed",
                key="fonte_envio_triagem",
            ) or OPCAO_ARQUIVO

        if fonte == OPCAO_ARQUIVO:
            chave_drop = "triagem_drop_compacta" if arquivos else "triagem_drop_vazia"
            with st.container(key=chave_drop):
                with st.container(key="triagem_drop"):
                    novos = st.file_uploader(
                        "Documento clínico",
                        type=EXTENSOES_ACEITAS,
                        accept_multiple_files=True,
                        label_visibility="collapsed",
                        key=f"uploader_triagem_{st.session_state[CHAVE_VERSAO_UPLOADER]}",
                    )
            if novos:
                existentes = {(a.name, a.size) for a in arquivos}
                for arq in novos:
                    if (arq.name, arq.size) not in existentes:
                        arquivos.append(
                            ArquivoCarregado(
                                name=arq.name,
                                size=arq.size,
                                type=arq.type or "",
                                dados=arq.getvalue(),
                            )
                        )
                # Reinicia o uploader para que a lista exibida seja só a nossa
                st.session_state[CHAVE_VERSAO_UPLOADER] += 1
                st.rerun()

            if arquivos:
                rotulo_qtd = "arquivo selecionado" if len(arquivos) == 1 else "arquivos selecionados"
                st.html(
                    f'<div class="triagem-contagem"><strong>{len(arquivos)} {rotulo_qtd}</strong>'
                    f"<span>{FORMATOS_TEXTO} · até 10 MB cada</span></div>"
                )
                for arq in arquivos:
                    extensao = arq.name.rsplit(".", 1)[-1].upper() if "." in arq.name else "DOC"
                    if arq.valido:
                        cor, status = "#107C41", "Pronto para análise"
                    else:
                        cor, status = "#B42318", "Não enviado: o arquivo passa de 10 MB"
                    with st.container(key=f"triagem_arq_{arq.id}"):
                        col_info, col_botao = st.columns([5, 1.1], vertical_alignment="center", gap="small")
                        with col_info:
                            st.html(
                                f"""
                                <div class="arq-linha">
                                    <div class="arq-badge">{escape(extensao)}</div>
                                    <div class="arq-info">
                                        <div class="arq-topo">
                                            <span class="arq-nome">{escape(arq.name)}</span>
                                            <span class="arq-tamanho">{formatar_tamanho(arq.size)}</span>
                                        </div>
                                        <div class="arq-barra" style="background:{cor};"></div>
                                        <div class="arq-status" style="color:{cor};">{status}</div>
                                    </div>
                                </div>
                                """
                            )
                        with col_botao:
                            st.button(
                                "Remover",
                                key=f"remover_{arq.id}",
                                on_click=_remover_arquivo,
                                args=(arq.id,),
                            )
        else:
            with st.container(key="triagem_texto"):
                texto_digitado = st.text_area(
                    "Texto do documento",
                    placeholder="Cole aqui o conteúdo do documento clínico...",
                    height=220,
                    label_visibility="collapsed",
                    key="area_texto_triagem",
                )

    arquivos_validos = [a for a in arquivos if a.valido]
    arquivos_invalidos = [a for a in arquivos if not a.valido]

    with col_direita:
        with st.container(key="triagem_acao"):
            if fonte == OPCAO_ARQUIVO:
                rotulo = "Analisar documentos" if len(arquivos) > 1 else "Analisar documento"
                desabilitado = not arquivos_validos
            else:
                rotulo = "Analisar documento"
                desabilitado = False
            analisar = st.button(rotulo, type="primary", disabled=desabilitado, key="btn_analisar_triagem")
        if fonte == OPCAO_ARQUIVO and arquivos_invalidos:
            texto_aviso = (
                "O arquivo com erro não entra na análise."
                if len(arquivos_invalidos) == 1
                else f"{len(arquivos_invalidos)} arquivos com erro não entram na análise."
            )
            st.html(f'<div class="triagem-aviso">{texto_aviso}</div>')

if analisar:
    if fonte == OPCAO_TEXTO and not texto_digitado.strip():
        st.warning("Cole o texto do documento para analisar.")
        st.stop()

    trabalhos = []
    lote_id = None
    if fonte == OPCAO_ARQUIVO:
        try:
            resposta_lote = enfileirar_documentos(arquivos_validos)
            lote_id = resposta_lote.get("lote_id")
            if lote_id:
                st.caption(f"Lote de processamento: `{lote_id}`")
            resultados_lote = resposta_lote.get("trabalhos") or [resposta_lote]
            for indice, resultado in enumerate(resultados_lote):
                nome = resultado.get("arquivo") or arquivos_validos[indice].name
                if resultado.get("status") != "na_fila":
                    st.error(f"{nome}: {resultado.get('erro', 'Não foi possível enfileirar o arquivo.')}")
                    continue
                trabalhos.append({
                    "documento_id": resultado["documento_id"],
                    "nome": nome,
                    "slot": st.empty(),
                })
        except ErroDeApi as erro:
            st.error(f"Não foi possível enviar o lote: {erro}")
    else:
        try:
            requisicao = montar_requisicao(None, texto_digitado)
            resposta = enfileirar_texto_documento(requisicao)
            lote_id = resposta.get("lote_id")
            trabalhos.append({
                "documento_id": resposta["documento_id"],
                "nome": "Texto colado",
                "slot": st.empty(),
            })
        except (ErroDeApi, ValueError, KeyError) as erro:
            st.error(f"Não foi possível iniciar a triagem do texto: {erro}")

    if not trabalhos:
        st.stop()

    pendentes = {item["documento_id"] for item in trabalhos}
    por_id = {item["documento_id"]: item for item in trabalhos}
    for item in trabalhos:
        item["slot"].info(f"{item['nome']}: aguardando processamento")

    inicio = time.monotonic()
    while pendentes and time.monotonic() - inicio < 1800:
        try:
            if lote_id:
                estado_lote = obter_status_triagem(lote_id)
                estados_documentos = estado_lote.get("trabalhos", [])
            else:
                estados_documentos = [
                    obter_status_triagem(documento_id) for documento_id in list(pendentes)
                ]
        except ErroDeApi as erro:
            st.error(f"Não foi possível consultar o lote: {erro}")
            break

        for estado in estados_documentos:
            documento_id = estado.get("documento_id")
            if documento_id not in pendentes:
                continue
            item = por_id[documento_id]
            if estado["status"] == "concluido":
                item["slot"].success(f"{item['nome']}: concluído · {documento_id}")
                if estado.get("resultado"):
                    exibir_resultado_da_triagem(estado["resultado"])
                pendentes.remove(documento_id)
            elif estado["status"] == "falhou":
                item["slot"].error(f"{item['nome']}: {estado.get('erro', 'Falha no processamento.')}")
                pendentes.remove(documento_id)
            else:
                _mostrar_andamento_trabalho(item["slot"], item["nome"], estado)
        if pendentes:
            time.sleep(2)

    if pendentes:
        for documento_id in pendentes:
            item = por_id[documento_id]
            item["slot"].warning(
                f"{item['nome']}: ainda está na fila. ID: {documento_id}. "
                "Consulte o histórico mais tarde."
            )
