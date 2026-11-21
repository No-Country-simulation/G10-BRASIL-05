"""Contrato da decisão pré-clínica do Harness."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class EvidenciaEscopo(BaseModel):
    fonte: Literal["texto", "visual"]
    categoria: Literal[
        "finalidade_clinica",
        "conteudo_clinico",
        "estrutura_medica",
        "conteudo_fora_escopo",
    ]
    citacao: Optional[str] = None
    observacao: Optional[str] = None

    @model_validator(mode="after")
    def validar_evidencia_observavel(self):
        if self.fonte == "texto" and not (self.citacao and self.citacao.strip()):
            raise ValueError("Evidência textual exige uma citação do documento.")
        if self.fonte == "visual" and not (self.observacao and self.observacao.strip()):
            raise ValueError("Evidência visual exige uma observação concreta.")
        return self


class ResultadoEscopoDocumento(BaseModel):
    escopo: Literal["medico", "nao_medico", "incerto"]
    legibilidade: Literal["legivel", "ilegivel", "indeterminada"]
    evidencias: list[EvidenciaEscopo] = Field(default_factory=list)
    justificativa: str = Field(min_length=1)

