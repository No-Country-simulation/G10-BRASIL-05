from sqlalchemy.orm import Session

from app.models.triagem import HospitalModel


def semear_hospitais(db: Session) -> None:
    if db.query(HospitalModel).count():
        return
    db.add_all(
        [
            HospitalModel(nome="Hospital Central MediFlow", cnpj="12.345.678/0001-90", cidade="São Paulo", uf="SP"),
            HospitalModel(nome="UPA Pronto Atendimento 24h", cnpj="98.765.432/0001-10", cidade="São Paulo", uf="SP"),
            HospitalModel(nome="Ambulatório Geral de Especialidades", cnpj="55.443.221/0001-33", cidade="Campinas", uf="SP"),
        ]
    )
