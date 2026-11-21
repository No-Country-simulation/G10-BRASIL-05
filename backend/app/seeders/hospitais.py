from sqlalchemy.orm import Session

from app.models.triagem import (
    CategoriaHospitalModel,
    CidadeModel,
    ClinicaModel,
    EstabelecimentoSaudeModel,
    HospitalModel,
)


HOSPITAIS_SEED = (
    ("Hospital Central MediFlow", "12.345.678/0001-90", "São Paulo", "SP", "HOSPITAL"),
    ("UPA Pronto Atendimento 24h", "98.765.432/0001-10", "São Paulo", "SP", "HOSPITAL"),
    ("Ambulatório Geral de Especialidades", "55.443.221/0001-33", "Campinas", "SP", "CLINICA"),
)


def semear_hospitais(db: Session) -> None:
    """Preserva os estabelecimentos originais, agora nas tabelas normalizadas da V4."""
    categoria = db.query(CategoriaHospitalModel).filter_by(nome="Geral").one_or_none()
    if categoria is None:
        categoria = CategoriaHospitalModel(nome="Geral", descricao="Categoria padrão dos hospitais seed")
        db.add(categoria)
        db.flush()

    for nome, cnpj, cidade_nome, uf, tipo in HOSPITAIS_SEED:
        existente = db.query(EstabelecimentoSaudeModel).filter_by(cnpj=cnpj).one_or_none()
        if existente:
            continue
        cidade = db.query(CidadeModel).filter_by(nome=cidade_nome, uf=uf).one_or_none()
        if cidade is None:
            cidade = CidadeModel(nome=cidade_nome, uf=uf)
            db.add(cidade)
            db.flush()
        estabelecimento = EstabelecimentoSaudeModel(
            tipo=tipo,
            nome=nome,
            cnpj=cnpj,
            cidade_id=cidade.id,
        )
        if tipo == "HOSPITAL":
            estabelecimento.hospital = HospitalModel(categoria_id=categoria.id)
        else:
            estabelecimento.clinica = ClinicaModel()
        db.add(estabelecimento)
    db.flush()
