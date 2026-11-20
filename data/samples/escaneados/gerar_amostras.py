"""Gera os documentos escaneados sintéticos usados para validar o OCR multimodal (SCRUM-96).

Todos os nomes, CRM e dados clínicos são fictícios. O texto não tem acentos porque a
fonte padrão do Pillow não desenha caracteres acentuados.
Uso: python data/samples/escaneados/gerar_amostras.py
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

PASTA = Path(__file__).resolve().parent

RECEITA_ESCANEADA = [
    "Receituario Medico",
    "",
    "Paciente: Fulano de Teste",
    "",
    "Uso oral:",
    "Amoxicilina 500mg",
    "1 capsula de 8/8h por 7 dias",
    "",
    "Dr. Ciclano Exemplo",
    "CRM 12345-MG",
]

LAUDO_ESCANEADO = [
    "LAUDO DE RADIOGRAFIA DE TORAX",
    "",
    "Paciente: Beltrana de Teste, 61 anos",
    "Medico: Dra. Fulana Exemplo  CRM 54321-SP",
    "",
    "Achados: consolidacao em lobo inferior direito.",
    "Conclusao: pneumonia adquirida na comunidade.",
    "CID: J18.9",
]


def _digitalizar(linhas, tamanho_fonte, inclinacao, tremor):
    """Desenha o texto e aplica inclinação, ruído e desfoque, imitando uma digitalização."""
    gerador = random.Random(42)
    fonte = ImageFont.load_default(size=tamanho_fonte)
    imagem = Image.new("L", (900, 80 + len(linhas) * int(tamanho_fonte * 1.6)), 245)
    desenho = ImageDraw.Draw(imagem)

    for indice, linha in enumerate(linhas):
        x = 50 + gerador.randint(-tremor, tremor)
        y = 40 + indice * int(tamanho_fonte * 1.6) + gerador.randint(-tremor, tremor)
        desenho.text((x, y), linha, fill=gerador.randint(20, 60), font=fonte)

    for _ in range(1500):
        desenho.point((gerador.randrange(imagem.width), gerador.randrange(imagem.height)), fill=gerador.randint(150, 220))

    imagem = imagem.rotate(inclinacao, expand=True, fillcolor=245, resample=Image.BICUBIC)
    return imagem.filter(ImageFilter.GaussianBlur(0.6)).convert("RGB")


def main():
    _digitalizar(RECEITA_ESCANEADA, 34, inclinacao=-2.5, tremor=6).save(PASTA / "receita_escaneada.png")
    _digitalizar(LAUDO_ESCANEADO, 26, inclinacao=1.2, tremor=1).save(PASTA / "laudo_escaneado.pdf", resolution=150)


if __name__ == "__main__":
    main()
