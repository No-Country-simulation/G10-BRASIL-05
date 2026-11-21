"""Preparação em memória da imagem para releitura visual de CPF."""

import io

from PIL import Image


def preparar_imagem_para_releitura(conteudo: bytes) -> bytes:
    """Converte a imagem inteira e amplia documentos pequenos quando útil.

    O pipeline não fornece coordenadas confiáveis do CPF; por isso, não cria
    recortes presumidos e mantém a página inteira como alternativa segura.
    """
    with Image.open(io.BytesIO(conteudo)) as imagem:
        imagem = imagem.convert("RGB")
        maior_dimensao = max(imagem.size)
        if maior_dimensao > 1600:
            imagem.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        elif maior_dimensao < 1200:
            escala = min(2, 2400 / maior_dimensao)
            tamanho = (round(imagem.width * escala), round(imagem.height * escala))
            imagem = imagem.resize(tamanho, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        imagem.save(buffer, format="JPEG", quality=92, optimize=True)
        return buffer.getvalue()
