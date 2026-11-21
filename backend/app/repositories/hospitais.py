from typing import List

from sqlalchemy.orm import Session

from app.models.triagem import (
    CategoriaHospitalModel,
    CidadeModel,
    EstabelecimentoSaudeModel,
    HospitalModel,
)


class HospitaisRepository:
    """Busca e cadastra hospitais pelo estabelecimento de saúde associado."""

    def __init__(self, db: Session):
        self.db = db

    def obter_ou_criar_hospital(self, nome_ou_canal: str) -> HospitalModel:
        nome = (nome_ou_canal or "Hospital Central MediFlow").replace("_", " ").title()
        hospital = (
            self.db.query(HospitalModel)
            .join(HospitalModel.estabelecimento)
            .filter(EstabelecimentoSaudeModel.nome.ilike(nome))
            .first()
        )
        if hospital:
            return hospital

        cidade = self.db.query(CidadeModel).filter_by(nome="São Paulo", uf="SP").one_or_none()
        if cidade is None:
            cidade = CidadeModel(nome="São Paulo", uf="SP")
            self.db.add(cidade)
            self.db.flush()
        categoria = self.db.query(CategoriaHospitalModel).filter_by(nome="Geral").one_or_none()
        if categoria is None:
            categoria = CategoriaHospitalModel(nome="Geral")
            self.db.add(categoria)
            self.db.flush()
        estabelecimento = EstabelecimentoSaudeModel(
            tipo="HOSPITAL", nome=nome, cidade_id=cidade.id
        )
        estabelecimento.hospital = HospitalModel(categoria_id=categoria.id)
        self.db.add(estabelecimento)
        self.db.flush()
        return estabelecimento.hospital

    def listar_hospitais(self) -> List[HospitalModel]:
        return (
            self.db.query(HospitalModel)
            .join(HospitalModel.estabelecimento)
            .filter(EstabelecimentoSaudeModel.ativo.is_(True))
            .all()
        )
