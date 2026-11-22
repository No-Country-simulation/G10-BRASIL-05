"""Modelos do domínio clínico e cadastral do MediFlow."""

from datetime import date

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey,
    Integer, String, Table, UniqueConstraint, func, text,
)
from sqlalchemy.orm import relationship, synonym

from app.models.base import Base

medico_especialidades = Table(
    "medico_especialidades",
    Base.metadata,
    Column("medico_id", ForeignKey("medicos.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True),
    Column("especialidade_id", ForeignKey("especialidades.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True),
)


class CidadeModel(Base):
    __tablename__ = "cidades"
    __table_args__ = (UniqueConstraint("nome", "uf", name="uq_cidades_nome_uf"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    uf = Column(String(2), nullable=False)


class EstabelecimentoSaudeModel(Base):
    __tablename__ = "estabelecimentos_saude"
    __table_args__ = (CheckConstraint("tipo IN ('HOSPITAL', 'CLINICA')", name="ck_estabelecimentos_tipo"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(String(20), nullable=False)
    nome = Column(String(180), nullable=False)
    cnpj = Column(String(30), unique=True)
    logradouro = Column(String(180))
    numero = Column(String(30))
    complemento = Column(String(120))
    bairro = Column(String(100))
    cep = Column(String(12))
    cidade_id = Column(Integer, ForeignKey("cidades.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False, index=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    cidade = relationship("CidadeModel")
    hospital = relationship("HospitalModel", back_populates="estabelecimento", uselist=False)
    clinica = relationship("ClinicaModel", back_populates="estabelecimento", uselist=False)


class CategoriaHospitalModel(Base):
    __tablename__ = "categorias_hospital"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(80), nullable=False, unique=True)
    descricao = Column(String(250))


class HospitalModel(Base):
    __tablename__ = "hospitais"

    estabelecimento_id = Column(Integer, ForeignKey("estabelecimentos_saude.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    categoria_id = Column(Integer, ForeignKey("categorias_hospital.id", ondelete="RESTRICT", onupdate="RESTRICT"))
    id = synonym("estabelecimento_id")

    estabelecimento = relationship("EstabelecimentoSaudeModel", back_populates="hospital")
    categoria = relationship("CategoriaHospitalModel")

    @property
    def nome(self) -> str | None:
        return self.estabelecimento.nome if self.estabelecimento else None

    @property
    def cnpj(self) -> str | None:
        return self.estabelecimento.cnpj if self.estabelecimento else None

    @property
    def cidade(self) -> str | None:
        return self.estabelecimento.cidade.nome if self.estabelecimento and self.estabelecimento.cidade else None

    @property
    def uf(self) -> str | None:
        return self.estabelecimento.cidade.uf if self.estabelecimento and self.estabelecimento.cidade else None

    @property
    def ativo(self) -> bool:
        return bool(self.estabelecimento.ativo) if self.estabelecimento else False


class ClinicaModel(Base):
    __tablename__ = "clinicas"

    estabelecimento_id = Column(Integer, ForeignKey("estabelecimentos_saude.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    estabelecimento = relationship("EstabelecimentoSaudeModel", back_populates="clinica")


class EspecialidadeModel(Base):
    __tablename__ = "especialidades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False, unique=True)
    medicos = relationship("MedicoModel", secondary=medico_especialidades, back_populates="especialidades")


class MedicoModel(Base):
    __tablename__ = "medicos"
    __table_args__ = (UniqueConstraint("crm", "uf", name="uq_medicos_crm_uf"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    crm = Column(String(30), nullable=False)
    uf = Column(String(2), nullable=False)
    nome = Column(String(150), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    especialidades = relationship("EspecialidadeModel", secondary=medico_especialidades, back_populates="medicos")
    documentos = relationship("DocumentoTriagemModel", back_populates="medico")

    @property
    def especialidade(self) -> str | None:
        nomes = [item.nome for item in self.especialidades]
        return " / ".join(nomes) if nomes else None


class EnfermeiroModel(Base):
    __tablename__ = "enfermeiros"
    __table_args__ = (UniqueConstraint("coren", "uf", name="uq_enfermeiros_coren_uf"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    coren = Column(String(30), nullable=False)
    uf = Column(String(2), nullable=False)
    nome = Column(String(150), nullable=False)
    area_atuacao = Column(String(100))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PacienteModel(Base):
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cpf = Column(String(20), unique=True, nullable=True)
    nome = Column(String(150), nullable=False)
    data_nascimento = Column(Date, nullable=True)
    cadastro_provisorio = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    documentos = relationship("DocumentoTriagemModel", back_populates="paciente")

    @property
    def idade(self) -> int | None:
        """Idade demográfica derivada da data de nascimento, nunca armazenada."""
        if self.data_nascimento is None:
            return None
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )


class EstabelecimentoProfissionalModel(Base):
    __tablename__ = "estabelecimento_profissionais"

    estabelecimento_id = Column(Integer, ForeignKey("estabelecimentos_saude.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    medico_id = Column(Integer, ForeignKey("medicos.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    inicio_vinculo = Column(DateTime(timezone=True), primary_key=True, nullable=False, server_default=func.now())
    fim_vinculo = Column(DateTime(timezone=True))
    funcao = Column(String(50))


class EstabelecimentoEnfermeiroModel(Base):
    __tablename__ = "estabelecimento_enfermeiros"

    estabelecimento_id = Column(Integer, ForeignKey("estabelecimentos_saude.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    enfermeiro_id = Column(Integer, ForeignKey("enfermeiros.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    inicio_vinculo = Column(DateTime(timezone=True), primary_key=True, nullable=False, server_default=func.now())
    fim_vinculo = Column(DateTime(timezone=True))
    funcao = Column(String(50))


class HospitalDiretorModel(Base):
    __tablename__ = "hospital_diretores"

    hospital_id = Column(Integer, ForeignKey("hospitais.estabelecimento_id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios_sistema.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    inicio_vinculo = Column(DateTime(timezone=True), primary_key=True, nullable=False, server_default=func.now())
    fim_vinculo = Column(DateTime(timezone=True))


__all__ = [
    "medico_especialidades",
    "CidadeModel",
    "CategoriaHospitalModel",
    "EstabelecimentoSaudeModel",
    "HospitalModel",
    "ClinicaModel",
    "EspecialidadeModel",
    "MedicoModel",
    "EnfermeiroModel",
    "PacienteModel",
    "EstabelecimentoProfissionalModel",
    "EstabelecimentoEnfermeiroModel",
    "HospitalDiretorModel",
]
