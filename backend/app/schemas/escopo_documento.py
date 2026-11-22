"""Contrato da decisão pré-clínica do Harness."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class EvidenciaEscopo(BaseModel):
    fonte: Literal["texto", "visual"] = "visual"
    categoria: Literal[
        "finalidade_clinica",
        "conteudo_clinico",
        "estrutura_medica",
        "conteudo_fora_escopo",
    ] = "conteudo_clinico"
    citacao: Optional[str] = None
    observacao: Optional[str] = None

    @field_validator("fonte", mode="before")
    @classmethod
    def normalizar_fonte(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip().lower() in {"texto", "visual"}:
            return v.strip().lower()
        return "visual"

    @field_validator("categoria", mode="before")
    @classmethod
    def normalizar_categoria(cls, v: Any) -> Any:
        categorias = {
            "finalidade_clinica",
            "conteudo_clinico",
            "estrutura_medica",
            "conteudo_fora_escopo",
        }
        if isinstance(v, str) and v.strip().lower() in categorias:
            return v.strip().lower()
        return "conteudo_clinico"

    @model_validator(mode="after")
    def validar_evidencia_observavel(self):
        if self.fonte == "texto" and not (self.citacao and self.citacao.strip()):
            if self.observacao and self.observacao.strip():
                self.citacao = self.observacao
            else:
                raise ValueError("Evidência textual exige uma citação do documento.")
        if self.fonte == "visual" and not (self.observacao and self.observacao.strip()):
            if self.citacao and self.citacao.strip():
                self.observacao = self.citacao
            else:
                raise ValueError("Evidência visual exige uma observação concreta.")
        return self


class ResultadoEscopoDocumento(BaseModel):
    escopo: Literal["medico", "nao_medico", "incerto"]
    legibilidade: Literal["legivel", "ilegivel", "indeterminada"]
    evidencias: list[EvidenciaEscopo] = Field(default_factory=list)
    justificativa: str = Field(min_length=1)

    @field_validator("evidencias", mode="before")
    @classmethod
    def normalizar_evidencias(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return list(v.values())
        if not isinstance(v, list):
            return []
        return v

    @field_validator("justificativa", mode="before")
    @classmethod
    def normalizar_justificativa(cls, v: Any) -> Any:
        if not v or not str(v).strip():
            return "Análise do escopo do documento realizada pela inteligência clínica."
        return str(v).strip()

    @field_validator("legibilidade", mode="before")
    @classmethod
    def normalizar_legibilidade(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_limpo = v.strip().lower()
            if v_limpo in {"legível", "legivel"}:
                return "legivel"
            if v_limpo in {"ilegível", "ilegivel"}:
                return "ilegivel"
            if v_limpo in {"indeterminada", "indeterminado"}:
                return "indeterminada"
        return v

