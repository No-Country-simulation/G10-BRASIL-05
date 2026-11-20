from typing import List

from sqlalchemy.orm import Session

from app.models.triagem import HospitalModel

class HospitaisRepository:
    """Busca, cadastra e lista hospitais ativos."""

    def __init__(self, db: Session):
        self.db = db

    def obter_ou_criar_hospital(self, nome_ou_canal: str) -> HospitalModel:
        """Busca unidade hospitalar ou cadastra o canal como polo de atendimento."""
        nome_limpo = (nome_ou_canal or "Hospital Central MediFlow").replace("_", " ").title()
        hospital = self.db.query(HospitalModel).filter(
            HospitalModel.nome.ilike(nome_limpo)
        ).first()

        if not hospital:
            hospital = HospitalModel(
                nome=nome_limpo,
                cidade="São Paulo",
                uf="SP",
                ativo=True,
            )
            self.db.add(hospital)
            self.db.flush()

        return hospital

    def listar_hospitais(self) -> List[HospitalModel]:
        return self.db.query(HospitalModel).filter(HospitalModel.ativo == True).all()
