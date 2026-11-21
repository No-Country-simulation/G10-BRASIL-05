"""Campos administrativos identificáveis exibidos na inspeção prévia."""

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class MetadadosInspecaoDocumento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numero_os: str | None = None
    nome_paciente: str | None = None
    idade_paciente: StrictInt | None = None
    medico_responsavel: str | None = None
    categoria_documento: str | None = None
    numero_passaporte: str | None = None
    data_passaporte: str | None = None
    tipo_data_passaporte: str | None = None
    evidencias: dict[str, str] = Field(default_factory=dict)
