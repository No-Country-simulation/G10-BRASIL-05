from datetime import date

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class PacienteExtraido(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nome: str | None = None
    cpf: str | None = Field(default=None, pattern=r"^\d{11}$")
    cns: str | None = Field(default=None, pattern=r"^\d{15}$", description="Cartão Nacional de Saúde (15 dígitos numéricos).")
    idade: StrictInt | None = None
    data_nascimento: date | None = None


class MedicoSolicitante(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nome: str | None = None
    crm_uf: str | None = Field(
        default=None,
        description="Registro profissional do médico no formato CRM-UF, quando informado.",
    )


class MedicamentoDosagem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    medicamento: str | None = None
    dosagem: str | None = None
    posologia: str | None = None


class DadosExtraidos(BaseModel):
    model_config = ConfigDict(extra="ignore")

    paciente: PacienteExtraido | None = None
    medico_solicitante: MedicoSolicitante | None = None
    exame_realizado: str | None = None
    diagnostico_principal: str | None = None
    cid_sugerido: str | None = None
    medicamentos: list[MedicamentoDosagem] = Field(default_factory=list)
