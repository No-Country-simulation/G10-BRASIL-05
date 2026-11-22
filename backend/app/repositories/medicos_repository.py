from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.clinico import EnfermeiroModel, EspecialidadeModel, MedicoModel


class MedicosRepository:
    """Busca e gerencia profissionais médicos e de enfermagem."""

    def __init__(self, db: Session):
        self.db = db

    def buscar_por_id(self, id: int) -> Optional[MedicoModel]:
        return self.db.query(MedicoModel).filter_by(id=id).first()

    def buscar_por_crm_uf(self, crm: str, uf: str) -> Optional[MedicoModel]:
        crm_limpo = (crm or "").strip()
        uf_limpo = (uf or "").strip().upper()
        return (
            self.db.query(MedicoModel)
            .filter(MedicoModel.crm == crm_limpo, MedicoModel.uf == uf_limpo)
            .first()
        )

    def criar_medico(
        self,
        nome: str,
        crm: str,
        uf: str,
        especialidade: Optional[str] = None,
    ) -> MedicoModel:
        medico = MedicoModel(
            nome=(nome or "").strip(),
            crm=(crm or "").strip(),
            uf=(uf or "").strip().upper(),
        )
        self.db.add(medico)
        self.db.flush()
        if especialidade:
            for item in (parte.strip() for parte in especialidade.split("/")):
                if not item:
                    continue
                esp = self.db.query(EspecialidadeModel).filter_by(nome=item).first()
                if esp is None:
                    esp = EspecialidadeModel(nome=item)
                    self.db.add(esp)
                    self.db.flush()
                if esp not in medico.especialidades:
                    medico.especialidades.append(esp)
        self.db.commit()
        self.db.refresh(medico)
        return medico

    def listar_medicos(self, skip: int = 0, limit: int = 50) -> List[MedicoModel]:
        return (
            self.db.query(MedicoModel)
            .order_by(MedicoModel.nome.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def buscar_enfermeiro_por_coren_uf(self, coren: str, uf: str) -> Optional[EnfermeiroModel]:
        coren_limpo = (coren or "").strip()
        uf_limpo = (uf or "").strip().upper()
        return (
            self.db.query(EnfermeiroModel)
            .filter(EnfermeiroModel.coren == coren_limpo, EnfermeiroModel.uf == uf_limpo)
            .first()
        )

    def criar_enfermeiro(
        self,
        nome: str,
        coren: str,
        uf: str,
        area_atuacao: Optional[str] = None,
    ) -> EnfermeiroModel:
        enfermeiro = EnfermeiroModel(
            nome=(nome or "").strip(),
            coren=(coren or "").strip(),
            uf=(uf or "").strip().upper(),
            area_atuacao=(area_atuacao or "").strip() or None,
        )
        self.db.add(enfermeiro)
        self.db.commit()
        self.db.refresh(enfermeiro)
        return enfermeiro

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
