import io
import os
from typing import Tuple
from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from PIL import Image

# Limite máximo de arquivo: 10 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

EXTENSOES_PERMITIDAS = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

MIME_TYPES_PERMITIDOS = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}


class DocumentParserService:
    """Serviço responsável pela validação, leitura e extração textual de PDFs e imagens clínicas."""

    @staticmethod
    def validar_arquivo(file: UploadFile, conteudo: bytes) -> str:
        """Valida extensão, tipo MIME e tamanho do arquivo enviado."""
        nome_arquivo = file.filename or ""
        extensao = os.path.splitext(nome_arquivo.lower())[1]

        if extensao not in EXTENSOES_PERMITIDAS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de arquivo '{extensao}' não suportado. Envie apenas arquivos PDF ou imagens (.png, .jpg, .jpeg, .webp).",
            )

        # Validação do Content-Type informado
        content_type = file.content_type or EXTENSOES_PERMITIDAS[extensao]
        if content_type.lower() not in MIME_TYPES_PERMITIDOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content-Type '{content_type}' inválido.",
            )

        # Validação de tamanho
        if len(conteudo) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O arquivo enviado está vazio.",
            )

        if len(conteudo) > MAX_FILE_SIZE_BYTES:
            tamanho_mb = len(conteudo) / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo excede o limite máximo permitido de 10 MB (tamanho atual: {tamanho_mb:.2f} MB).",
            )

        return extensao

    @staticmethod
    def extrair_texto(conteudo: bytes, extensao: str, nome_arquivo: str) -> Tuple[str, str]:
        """Extrai o texto clínico do conteúdo binário.

        Retorna:
            Tuple[str, str]: (texto_extraido, tipo_arquivo)
        """
        if extensao == ".pdf":
            try:
                reader = PdfReader(io.BytesIO(conteudo))
                paginas_texto = []
                for idx, page in enumerate(reader.pages):
                    texto_pagina = page.extract_text()
                    if texto_pagina and texto_pagina.strip():
                        paginas_texto.append(texto_pagina.strip())

                texto_completo = "\n\n".join(paginas_texto)
                if not texto_completo.strip():
                    # PDF puramente escaneado sem camada de texto vetorial
                    texto_completo = (
                        f"[Documento PDF Escaneado: {nome_arquivo} - Sem camada de texto nativa. "
                        "Encaminhado para auditoria humana / OCR multimodal]"
                    )

                return texto_completo, "pdf"
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Não foi possível processar o arquivo PDF '{nome_arquivo}': {str(e)}",
                )

        else:
            # Imagem (PNG, JPEG, WebP)
            try:
                img = Image.open(io.BytesIO(conteudo))
                img.verify()  # Valida integridade da imagem

                # Reabre pois verify() invalida o ponteiro para leitura posterior
                img = Image.open(io.BytesIO(conteudo))
                formato = img.format or "IMAGEM"
                largura, altura = img.size

                texto_imagem = (
                    f"[Documento Clínico Imagem: {nome_arquivo} | Formato: {formato} | "
                    f"Dimensões: {largura}x{altura} px - Aguardando OCR / Visão Computacional]"
                )
                return texto_imagem, "imagem"
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Arquivo de imagem corrompido ou inválido '{nome_arquivo}': {str(e)}",
                )
