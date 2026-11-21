from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PapelUsuario = Literal["ADMIN_GERAL", "DIRETOR", "MEDICO", "ENFERMEIRO", "INSTITUCIONAL_WHATSAPP"]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=150)
    senha: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if "@" not in valor or "." not in valor.rsplit("@", 1)[-1]:
            raise ValueError("Informe um e-mail válido.")
        return valor


class AlterarSenhaRequest(BaseModel):
    nova_senha: str = Field(min_length=12, max_length=256)


class UsuarioAutenticado(BaseModel):
    id: str
    nome: str
    email: str
    nivel: PapelUsuario
    trocar_senha_obrigatorio: bool
    registro: str = ""
    especialidade: str = ""


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    usuario: UsuarioAutenticado


class UsuarioProvisionarRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: str
    senha: str = Field(min_length=12, max_length=256)
    nivel: Literal["DIRETOR", "MEDICO", "ENFERMEIRO"]
    registro: str = Field(default="", max_length=100)
    especialidade: str = Field(default="", max_length=150)

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if "@" not in valor or "." not in valor.rsplit("@", 1)[-1]:
            raise ValueError("Informe um e-mail válido.")
        return valor


class UsuarioAtualizarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=2, max_length=150)
    email: str | None = None
    senha: str | None = Field(default=None, min_length=12, max_length=256)
    nivel: Literal["DIRETOR", "MEDICO", "ENFERMEIRO"] | None = None
    registro: str | None = Field(default=None, max_length=100)
    especialidade: str | None = Field(default=None, max_length=150)
    ativo: bool | None = None

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.strip().lower()
        if "@" not in valor or "." not in valor.rsplit("@", 1)[-1]:
            raise ValueError("Informe um e-mail válido.")
        return valor

    @model_validator(mode="after")
    def rejeitar_nulos_explicitos(self):
        if any(valor is None for valor in self.model_dump(exclude_unset=True).values()):
            raise ValueError("Campos enviados não podem ser nulos.")
        return self
