import re
from typing import List, Optional
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.triagem import DocumentoTriagemModel, PacienteModel

class PacientesRepository:
    """Busca, cadastra e lista pacientes e seus documentos."""

    def __init__(self, db: Session):
        self.db = db

    def obter_ou_criar_paciente(
        self,
        nome: str,
        idade: Optional[int] = None,
        cpf: Optional[str] = None,
        data_nascimento: Optional[date] = None,
    ) -> Optional[PacienteModel]:
        """Busca paciente existente ou cria novo cadastro (provisório se sem CPF)."""
        digitos_cpf = re.sub(r"\D", "", cpf) if cpf else ""
        cpf = digitos_cpf if len(digitos_cpf) == 11 else None
        paciente = None
        if cpf:
            paciente = self.db.query(PacienteModel).filter(PacienteModel.cpf == cpf).first()

        if not paciente and nome:
            candidatos = self.buscar_por_nome(nome)
            # Nome não é identificador único: só reutiliza cadastro sem CPF se houver um único.
            paciente = candidatos[0] if len(candidatos) == 1 else None
            if len(candidatos) > 1:
                return None

        if not paciente:
            if data_nascimento is None and idade is not None:
                hoje = date.today()
                data_nascimento = date(hoje.year - idade, hoje.month, hoje.day)
            paciente = PacienteModel(
                nome=nome.strip() if nome else "Paciente Não Identificado",
                cpf=cpf,
                data_nascimento=data_nascimento,
                cadastro_provisorio=True if not cpf else False,
            )
            self.db.add(paciente)
            self.db.flush()
        elif data_nascimento is not None and paciente.data_nascimento is None:
            paciente.data_nascimento = data_nascimento
        elif idade is not None and paciente.data_nascimento is None:
            hoje = date.today()
            paciente.data_nascimento = date(hoje.year - idade, hoje.month, hoje.day)

        return paciente

    def buscar_por_nome(self, nome: str) -> List[PacienteModel]:
        """Busca igualdade de nome sem criar registros e limita a 2 para detectar ambiguidade."""
        nome_normalizado = nome.strip().casefold()
        if not nome_normalizado:
            return []
        return (
            self.db.query(PacienteModel)
            .filter(func.lower(PacienteModel.nome) == nome_normalizado.lower())
            .order_by(PacienteModel.id.asc())
            .limit(2)
            .all()
        )

    def listar_pacientes(self, skip: int = 0, limit: int = 50) -> List[PacienteModel]:
        return (
            self.db.query(PacienteModel)
            .order_by(PacienteModel.nome.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def buscar_paciente_por_id(self, paciente_id: int) -> Optional[PacienteModel]:
        return self.db.query(PacienteModel).filter(PacienteModel.id == paciente_id).first()

    def listar_historico_paciente(self, paciente_id: int) -> List[DocumentoTriagemModel]:
        return (
            self.db.query(DocumentoTriagemModel)
            .filter(DocumentoTriagemModel.paciente_id == paciente_id)
            .order_by(DocumentoTriagemModel.created_at.desc())
            .all()
        )
