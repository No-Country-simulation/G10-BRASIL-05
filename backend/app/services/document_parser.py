import base64
import io
import os
from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from PIL import Image

from app.schemas.ingestao import DocumentoIngerido, FormatoDocumento, ImagemDocumento

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
    def preparar_documento(conteudo: bytes, extensao: str, nome_arquivo: str) -> DocumentoIngerido:
        """Converte o arquivo enviado no formato padronizado da ingestão (SCRUM-56).

        - PDF com camada de texto: texto extraído das páginas.
        - PDF escaneado (sem texto): imagens das páginas, para leitura multimodal.
        - Imagem: a própria imagem, para leitura multimodal.
        """
        if extensao == ".pdf":
            return DocumentParserService._preparar_pdf(conteudo, nome_arquivo)
        return DocumentParserService._preparar_imagem(conteudo, extensao, nome_arquivo)

    @staticmethod
    def _preparar_pdf(conteudo: bytes, nome_arquivo: str) -> DocumentoIngerido:
        try:
            reader = PdfReader(io.BytesIO(conteudo))
            paginas_texto = [
                texto.strip() for texto in (page.extract_text() for page in reader.pages) if texto and texto.strip()
            ]
            if paginas_texto:
                return DocumentoIngerido(formato=FormatoDocumento.PDF, texto="\n\n".join(paginas_texto))

            imagens = [
                ImagemDocumento(
                    mime_type=EXTENSOES_PERMITIDAS.get(os.path.splitext(imagem.name.lower())[1], "image/png"),
                    dados_base64=base64.b64encode(imagem.data).decode("ascii"),
                )
                for page in reader.pages
                for imagem in page.images
            ]
            return DocumentoIngerido(formato=FormatoDocumento.PDF, imagens=imagens)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Não foi possível processar o arquivo PDF '{nome_arquivo}': {str(e)}",
            )

    @staticmethod
    def _preparar_imagem(conteudo: bytes, extensao: str, nome_arquivo: str) -> DocumentoIngerido:
        try:
            Image.open(io.BytesIO(conteudo)).verify()  # Valida integridade da imagem
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Arquivo de imagem corrompido ou inválido '{nome_arquivo}': {str(e)}",
            )

        imagem = ImagemDocumento(
            mime_type=EXTENSOES_PERMITIDAS[extensao],
            dados_base64=base64.b64encode(conteudo).decode("ascii"),
        )
        return DocumentoIngerido(formato=FormatoDocumento.IMAGEM, imagens=[imagem])
