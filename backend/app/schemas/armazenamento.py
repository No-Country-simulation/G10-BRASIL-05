from pydantic import BaseModel, Field


class ArmazenamentoOCI(BaseModel):
    """Metadados e confirmação de persistência segregada no Oracle Cloud Infrastructure Object Storage (SCRUM-52)."""
    bucket: str = Field(
        ...,
        example="mediflow-documentos-clinicos",
        description="Nome do bucket OCI Always Free onde o JSON foi gravado",
    )
    caminho_objeto: str = Field(
        ...,
        example="processados/urgentes/DOC-CLIN-2026-8942.json",
        description="Caminho segregado do objeto conforme o status e nível de prioridade",
    )
    status_backup: str = Field(
        ...,
        example="sucesso",
        description="Confirmação do status da operação de escrita no storage",
    )
