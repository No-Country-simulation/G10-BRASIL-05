"""Módulo de processamento e otimização de imagens para reconhecimento óptico de caracteres (OCR).

Contém rotinas para conversão em escala de cinza, ajuste de contraste e
binarização de documentos digitalizados.
"""

import io
import logging

logger = logging.getLogger(__name__)


def ajustar_contraste_ocr(imagem_bytes: bytes) -> bytes:
    """Aprimora a qualidade de imagem para operações de OCR.

    Realiza:
    - Leitura dos bytes da imagem
    - Conversão para escala de cinza
    - Autocontraste e ajuste de contraste
    - Retorno dos bytes processados em formato PNG

    Args:
        imagem_bytes: Bytes da imagem original (JPEG, PNG, HEIC, TIFF, etc.).

    Returns:
        bytes: Imagem processada em bytes, otimizada para OCR (em formato PNG).

    Raises:
        ValueError: Caso os bytes fornecidos sejam inválidos ou vazios.
    """
    if not imagem_bytes or not isinstance(imagem_bytes, bytes):
        raise ValueError("Os bytes da imagem não podem ser vazios ou nulos.")

    try:
        from PIL import Image, ImageEnhance, ImageOps

        # Carrega a imagem a partir dos bytes
        with Image.open(io.BytesIO(imagem_bytes)) as img:
            # Converte para escala de cinza ('L')
            if img.mode != "L":
                img = img.convert("L")

            # Aplica autocontraste para remover sombras sutis e clarear fundo
            img = ImageOps.autocontrast(img, cutoff=2)

            # Aumenta contraste para destacar textos escuros
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.8)

            # Exporta para PNG de alta fidelidade
            buffer_saida = io.BytesIO()
            img.save(buffer_saida, format="PNG", optimize=True)
            return buffer_saida.getvalue()

    except Exception as exc:
        logger.error("Erro ao aplicar ajustes de contraste para OCR: %s", exc)
        raise ValueError(f"Não foi possível processar a imagem para OCR: {exc}") from exc
