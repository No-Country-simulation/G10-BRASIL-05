from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.triagem import EspecialidadeModel, MedicoModel


class MedicosRepository:
    """Busca e cadastra médicos com especialidades normalizadas."""

    def __init__(self, db: Session):
        self.db = db

    def obter_ou_criar_medico(
        self, nome: str, crm: str, especialidade: Optional[str] = None
    ) -> MedicoModel:
        crm_formatado = crm.strip().upper() if crm else "CRM-INDEFINIDO"
        uf = crm_formatado.rsplit("-", 1)[-1] if "-" in crm_formatado else "SP"
        numero = crm_formatado.rsplit("-", 1)[0] if "-" in crm_formatado else crm_formatado
        numero = numero.removeprefix("CRM ").removeprefix("CRM-").strip()
        medico = (
            self.db.query(MedicoModel)
            .filter(MedicoModel.crm == numero, MedicoModel.uf == uf)
            .first()
        )
        if medico is None:
            medico = MedicoModel(
                nome=nome.strip() if nome else "Médico Solicitante", crm=numero, uf=uf
            )
            self.db.add(medico)
            self.db.flush()
        if especialidade:
            for item in (parte.strip() for parte in especialidade.split("/")):
                if not item:
                    continue
                registro = self.db.query(EspecialidadeModel).filter_by(nome=item).one_or_none()
                if registro is None:
                    registro = EspecialidadeModel(nome=item)
                    self.db.add(registro)
                    self.db.flush()
                if registro not in medico.especialidades:
                    medico.especialidades.append(registro)
        return medico

    def buscar_por_crm(self, crm: str) -> Optional[MedicoModel]:
        if not crm:
            return None
        texto = crm.strip().upper()
        uf = texto.rsplit("-", 1)[-1] if "-" in texto else "SP"
        numero = texto.rsplit("-", 1)[0] if "-" in texto else texto
        numero = numero.removeprefix("CRM ").removeprefix("CRM-").strip()
        return self.db.query(MedicoModel).filter_by(crm=numero, uf=uf).first()

    def listar_medicos(self, skip: int = 0, limit: int = 50) -> List[MedicoModel]:
        return (
            self.db.query(MedicoModel)
            .order_by(MedicoModel.nome.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
