from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.triagem import MedicoModel

class MedicosRepository:
    """Busca, cadastra e lista médicos do corpo clínico."""

    def __init__(self, db: Session):
        self.db = db

    def obter_ou_criar_medico(
        self,
        nome: str,
        crm: str,
        especialidade: Optional[str] = None,
    ) -> MedicoModel:
        """Busca médico por CRM único ou registra novo no corpo clínico."""
        crm_formatado = crm.strip().upper() if crm else "CRM-INDEFINIDO"
        medico = self.db.query(MedicoModel).filter(MedicoModel.crm == crm_formatado).first()

        if not medico:
            uf = "SP"
            if "-" in crm_formatado:
                partes = crm_formatado.split("-")
                if len(partes) > 1 and len(partes[-1]) == 2:
                    uf = partes[-1]

            medico = MedicoModel(
                nome=nome.strip() if nome else "Médico Solicitante",
                crm=crm_formatado,
                especialidade=especialidade or "Clínica Médica",
                uf=uf,
            )
            self.db.add(medico)
            self.db.flush()

        return medico

    def buscar_por_crm(self, crm: str) -> Optional[MedicoModel]:
        """Busca por CRM exato, sem criar nem alterar registros."""
        crm_formatado = crm.strip().upper() if crm else ""
        if not crm_formatado:
            return None
        return self.db.query(MedicoModel).filter(MedicoModel.crm == crm_formatado).first()

    def listar_medicos(self, skip: int = 0, limit: int = 50) -> List[MedicoModel]:
        return (
            self.db.query(MedicoModel)
            .order_by(MedicoModel.nome.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
