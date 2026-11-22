import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.clinico import EnfermeiroModel, EspecialidadeModel, MedicoModel


UFS_BRASIL = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


def extrair_crm_e_uf(crm_texto: str | None) -> tuple[str, str]:
    """Extrai número limpo do CRM e sigla da UF com segurança (tamanho máximo 2)."""
    if not crm_texto:
        return "INDEFINIDO", "SP"

    texto = str(crm_texto).strip().upper()
    uf_encontrada = "SP"
    tokens = re.split(r"[\s\-\/\.]+", texto)
    for token in tokens:
        if token in UFS_BRASIL:
            uf_encontrada = token
            break

    numeros = "".join(ch for ch in texto if ch.isdigit())
    if not numeros:
        palavras = [t for t in tokens if t not in {"CRM", uf_encontrada} and t]
        numeros = "".join(palavras)[:20] or "INDEFINIDO"

    return numeros[:20], uf_encontrada[:2]


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
        uf_limpa = (uf or "SP").strip().upper()[:2]
        medico = MedicoModel(
            nome=(nome or "").strip()[:150],
            crm=(crm or "").strip()[:50],
            uf=uf_limpa,
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
        numero, uf = extrair_crm_e_uf(crm)
        medico = (
            self.db.query(MedicoModel)
            .filter(MedicoModel.crm == numero, MedicoModel.uf == uf)
            .first()
        )
        if medico is None:
            medico = MedicoModel(
                nome=(nome or "Médico Solicitante").strip()[:150],
                crm=numero,
                uf=uf,
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
        numero, uf = extrair_crm_e_uf(crm)
        return self.db.query(MedicoModel).filter_by(crm=numero, uf=uf).first()
