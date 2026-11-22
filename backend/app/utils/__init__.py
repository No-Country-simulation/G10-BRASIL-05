"""Pacote de utilitários globais do sistema MediFlow.

Exporta funções de validação de documentos, consulta de endereços (CEP),
manipulação e sanitização de texto, e otimização de imagem para OCR.
"""

from app.utils.cep import buscar_cep
from app.utils.imagem import ajustar_contraste_ocr
from app.utils.texto import (
    normalizar_espacos,
    remover_acentos,
    sanitizar_texto_clinico,
)
from app.utils.validadores import (
    formatar_cpf,
    validar_coren,
    validar_cpf,
    validar_crm,
    validar_email,
)

__all__ = [
    # Validações e formatações
    "validar_cpf",
    "formatar_cpf",
    "validar_crm",
    "validar_coren",
    "validar_email",
    # CEP
    "buscar_cep",
    # Texto
    "remover_acentos",
    "normalizar_espacos",
    "sanitizar_texto_clinico",
    # Imagem
    "ajustar_contraste_ocr",
]
