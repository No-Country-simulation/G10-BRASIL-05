import io
import os
from typing import Tuple, Optional
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
    def validar_bytes(
        conteudo: bytes,
        nome_arquivo: str = "documento",
        content_type: Optional[str] = None,
    ) -> str:
        """Valida extensão, tipo MIME e tamanho de um buffer de bytes."""
        extensao = os.path.splitext(nome_arquivo.lower())[1]

        # Se o nome do arquivo não tiver extensão mas tiver content_type, deduz extensão
        if not extensao and content_type:
            tipo_para_ext = {v: k for k, v in EXTENSOES_PERMITIDAS.items()}
            extensao = tipo_para_ext.get(content_type.lower(), "")

        if extensao not in EXTENSOES_PERMITIDAS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de arquivo '{extensao}' não suportado. Envie apenas arquivos PDF ou imagens (.png, .jpg, .jpeg, .webp).",
            )

        # Validação do Content-Type informado
        ct = content_type or EXTENSOES_PERMITIDAS.get(extensao)
        if ct and ct.lower() not in MIME_TYPES_PERMITIDOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content-Type '{ct}' inválido.",
            )

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
    def validar_arquivo(file: UploadFile, conteudo: bytes) -> str:
        """Valida extensão, tipo MIME e tamanho do arquivo enviado via UploadFile."""
        return DocumentParserService.validar_bytes(
            conteudo=conteudo,
            nome_arquivo=file.filename or "",
            content_type=file.content_type,
        )

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

                texto_imagem = DocumentParserService.extrair_texto_imagem(
                    conteudo=conteudo,
                    extensao=extensao,
                    nome_arquivo=nome_arquivo,
                )
                return texto_imagem, "imagem"
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Arquivo de imagem corrompido ou inválido '{nome_arquivo}': {str(e)}",
                )

    @staticmethod
    def extrair_texto_imagem(conteudo: bytes, extensao: str, nome_arquivo: str) -> str:
        """Utiliza visão computacional / LLM multimodal para transcrever com precisão o documento clínico."""
        import base64
        try:
            from app.config.settings import settings
            from app.config.logger import logger
        except ImportError:
            from backend.app.config.settings import settings
            from backend.app.config.logger import logger

        mimetype_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }
        mime = mimetype_map.get(extensao.lower(), "image/jpeg")

        # Tenta transcrição via modelo multimodal configurado se as credenciais estiverem disponíveis
        if settings.OPENROUTER_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                from langchain_core.messages import HumanMessage

                # Otimiza imagem para envio ao modelo de visão se for muito grande
                try:
                    img_pil = Image.open(io.BytesIO(conteudo))
                    if img_pil.mode in ("RGBA", "P"):
                        img_pil = img_pil.convert("RGB")
                    max_dim = 1600
                    if max(img_pil.width, img_pil.height) > max_dim:
                        img_pil.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                        buffer = io.BytesIO()
                        img_pil.save(buffer, format="JPEG", quality=90)
                        conteudo = buffer.getvalue()
                        mime = "image/jpeg"
                except Exception as img_err:
                    logger.debug(f"Aviso ao otimizar imagem para OCR: {img_err}")

                b64 = base64.b64encode(conteudo).decode("utf-8")
                modelo = settings.OPENROUTER_MODEL or "google/gemma-3-27b-it"
                llm = ChatOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.OPENROUTER_API_KEY,
                    model=modelo,
                    temperature=0.0,
                    timeout=35.0,
                    default_headers={
                        "HTTP-Referer": "http://localhost:8000",
                        "X-Title": "MediFlow OCR",
                    },
                )
                msg = HumanMessage(content=[
                    {
                        "type": "text",
                        "text": (
                            "Você é um especialista em transcrição e OCR de documentos médicos e laudos clínicos. "
                            "Transcreva rigorosamente todo o texto legível presente nesta imagem médica "
                            "(incluindo nomes de paciente e médico, CRM, medicamentos, posologia, exames, diagnósticos e carimbos). "
                            "Se a imagem não contiver texto legível, retorne uma breve descrição clínica. "
                            "Retorne apenas o texto transcrito, sem introduções adicionais."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ])
                resp = llm.invoke([msg])
                texto = resp.content if isinstance(resp.content, str) else str(resp.content)
                if texto and len(texto.strip()) > 3:
                    logger.info(f"Transcrição visual da imagem '{nome_arquivo}' concluída com sucesso ({len(texto.strip())} chars).")
                    return texto.strip()
            except Exception as e:
                logger.warning(f"Falha ao executar OCR multimodal para '{nome_arquivo}': {e}")

        # Fallback descritivo para casos sem transcrição multimodal ou imagem sem texto
        try:
            img = Image.open(io.BytesIO(conteudo))
            largura, altura = img.size
            formato = img.format or extensao.replace(".", "").upper()
        except Exception:
            largura, altura, formato = 0, 0, "IMAGEM"

        return (
            f"[Documento Clínico Imagem: {nome_arquivo} | Formato: {formato} | "
            f"Dimensões: {largura}x{altura} px - Aguardando auditoria médica manual / OCR]"
        )
