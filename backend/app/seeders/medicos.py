from sqlalchemy.orm import Session

from app.models.triagem import MedicoModel


def semear_medicos(db: Session) -> None:
    if db.query(MedicoModel).count():
        return
    db.add_all(
        [
            MedicoModel(nome="Dra. Renata Silveira", crm="145892-SP", especialidade="Radiologia / Pneumologia", uf="SP"),
            MedicoModel(nome="Dr. Lucas Ramos", crm="87654-SP", especialidade="Clínica Médica", uf="SP"),
            MedicoModel(nome="Dr. Roberto Silva", crm="112233-SP", especialidade="Auditoria Médica", uf="SP"),
        ]
    )
