
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class RequisicaoDocumento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documento_id: str
    tipo_arquivo: Literal["PDF", "IMAGEM", "TEXTO", "JSON"]
    documento_texto: str
    canal_origem: str

    @field_validator(
        "documento_id",
        "documento_texto",
        "canal_origem",
    )
    @classmethod
    def rejeitar_texto_vazio(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("O campo não pode estar vazio.")
        return valor
