from pydantic import BaseModel, ConfigDict, Field


class MedicoSolicitante(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = None
    crm_uf: str | None = Field(
        default=None,
        description="Registro profissional do médico no formato CRM-UF, quando informado.",
    )


class MedicamentoDosagem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medicamento: str | None = None
    dosagem: str | None = None


class DadosExtraidos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paciente: str | None = None
    medico_solicitante: MedicoSolicitante | None = None
    exame_realizado: str | None = None
    diagnostico_principal: str | None = None
    cid_sugerido: str | None = None
    medicamentos: list[MedicamentoDosagem] = Field(default_factory=list)
