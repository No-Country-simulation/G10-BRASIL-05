from sqlalchemy.orm import Session

from app.models.triagem import EspecialidadeModel, MedicoModel


MEDICOS_SEED = (
    ("Dra. Renata Silveira", "145892", "SP", ("Radiologia", "Pneumologia")),
    ("Dr. Lucas Ramos", "87654", "SP", ("Clínica Médica",)),
    ("Dr. Roberto Silva", "112233", "SP", ("Auditoria Médica",)),
)


def semear_medicos(db: Session) -> None:
    """Mantém os mesmos profissionais e especialidades com relações normalizadas."""
    for nome, crm, uf, nomes_especialidades in MEDICOS_SEED:
        medico = db.query(MedicoModel).filter_by(crm=crm, uf=uf).one_or_none()
        if medico is None:
            medico = MedicoModel(nome=nome, crm=crm, uf=uf)
            db.add(medico)
            db.flush()
        else:
            medico.nome = nome
        for nome_especialidade in nomes_especialidades:
            especialidade = db.query(EspecialidadeModel).filter_by(nome=nome_especialidade).one_or_none()
            if especialidade is None:
                especialidade = EspecialidadeModel(nome=nome_especialidade)
                db.add(especialidade)
                db.flush()
            if especialidade not in medico.especialidades:
                medico.especialidades.append(especialidade)
    db.flush()
