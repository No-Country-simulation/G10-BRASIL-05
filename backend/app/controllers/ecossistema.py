from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.repositories.database import get_db, DatabaseRepository
from app.schemas.ecossistema import (
    PacienteResponse,
    MedicoResponse,
    HospitalResponse,
    PacienteHistoricoResponse,
    DocumentoHistoricoItem,
)

router = APIRouter(tags=["Ecossistema Clínico (Hospitais, Médicos e Pacientes)"])


@router.get("/pacientes", response_model=List[PacienteResponse], status_code=status.HTTP_200_OK)
def listar_pacientes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lista todos os pacientes registrados no prontuário unificado MediFlow."""
    repo = DatabaseRepository(db)
    return repo.listar_pacientes(skip=skip, limit=limit)


@router.get("/pacientes/{paciente_id}", response_model=PacienteResponse, status_code=status.HTTP_200_OK)
def obter_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
):
    """Consulta detalhes cadastrais de um paciente pelo ID."""
    repo = DatabaseRepository(db)
    paciente = repo.buscar_paciente_por_id(paciente_id)
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paciente com ID {paciente_id} não encontrado.",
        )
    return paciente


@router.get(
    "/pacientes/{paciente_id}/historico",
    response_model=PacienteHistoricoResponse,
    status_code=status.HTTP_200_OK,
)
def obter_historico_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
):
    """Retorna a visão longitudinal de todos os laudos, receitas e exames de um paciente."""
    repo = DatabaseRepository(db)
    paciente = repo.buscar_paciente_por_id(paciente_id)
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paciente com ID {paciente_id} não encontrado.",
        )

    documentos = repo.listar_historico_paciente(paciente_id)
    historico_items = [
        DocumentoHistoricoItem(
            documento_id=doc.documento_id,
            tipo_documento=doc.tipo_documento,
            nivel_prioridade=doc.nivel_prioridade,
            status_processamento=doc.status_processamento,
            score_confianca=doc.score_confianca,
            destino_principal=doc.destino_principal,
            created_at=doc.created_at,
            dados_extraidos=doc.dados_extraidos,
        )
        for doc in documentos
    ]

    return PacienteHistoricoResponse(
        paciente=PacienteResponse.model_validate(paciente),
        total_documentos=len(historico_items),
        historico=historico_items,
    )


@router.get("/medicos", response_model=List[MedicoResponse], status_code=status.HTTP_200_OK)
def listar_medicos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lista o corpo clínico cadastrado no sistema com CRM e especialidade."""
    repo = DatabaseRepository(db)
    return repo.listar_medicos(skip=skip, limit=limit)


@router.get("/hospitais", response_model=List[HospitalResponse], status_code=status.HTTP_200_OK)
def listar_hospitais(db: Session = Depends(get_db)):
    """Lista todas as unidades hospitalares e polos de atendimento cadastrados."""
    repo = DatabaseRepository(db)
    return repo.listar_hospitais()
