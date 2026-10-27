from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class HospitalModel(Base):
    """Unidades hospitalares e canais de atendimento credenciados."""
    __tablename__ = "hospitais"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(150), unique=True, index=True, nullable=False)
    cnpj = Column(String(30), unique=True, nullable=True)
    cidade = Column(String(100), default="São Paulo")
    uf = Column(String(2), default="SP")
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    documentos = relationship("DocumentoTriagemModel", back_populates="hospital")


class MedicoModel(Base):
    """Corpo clínico e médicos solicitantes/auditores."""
    __tablename__ = "medicos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    crm = Column(String(30), unique=True, index=True, nullable=False)
    nome = Column(String(150), nullable=False)
    especialidade = Column(String(100), default="Clínica Médica")
    uf = Column(String(2), default="SP")
    created_at = Column(DateTime, default=datetime.utcnow)

    documentos = relationship("DocumentoTriagemModel", back_populates="medico")


class PacienteModel(Base):
    """Prontuário unificado de pacientes."""
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cpf = Column(String(20), unique=True, index=True, nullable=True)
    nome = Column(String(150), nullable=False, index=True)
    idade = Column(Integer, nullable=True)
    cadastro_provisorio = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documentos = relationship("DocumentoTriagemModel", back_populates="paciente")


class DocumentoTriagemModel(Base):
    """Tabela principal de armazenamento de triagens clínicas processadas."""
    __tablename__ = "documentos_triagem"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    documento_id = Column(String(100), unique=True, index=True, nullable=False)
    tipo_arquivo = Column(String(50), nullable=False)
    canal_origem = Column(String(100), default="Pronto_Socorro")
    documento_texto = Column(Text, nullable=True)

    # Chaves Estrangeiras do Ecossistema Relacional
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitais.id"), nullable=True, index=True)

    # Classificação
    tipo_documento = Column(String(100), nullable=True)
    especialidade = Column(String(100), nullable=True)
    nivel_prioridade = Column(String(50), default="Rotina")
    score_confianca = Column(Float, default=1.0)

    # Roteamento & Auditoria
    destino_principal = Column(String(100), nullable=True)
    requer_auditoria_humana = Column(Boolean, default=False, index=True)
    status_processamento = Column(String(50), default="processado", index=True)
    justificativa_roteamento = Column(Text, nullable=True)

    # Entidades extraídas (armazenamento flexível em JSON)
    dados_extraidos = Column(JSON, nullable=True)

    # OCI Object Storage
    bucket_oci = Column(String(150), nullable=True)
    caminho_objeto_oci = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos ORM
    paciente = relationship("PacienteModel", back_populates="documentos")
    medico = relationship("MedicoModel", back_populates="documentos")
    hospital = relationship("HospitalModel", back_populates="documentos")


class TrilhaAuditoriaModel(Base):
    """Trilha de auditoria para conformidade LGPD e decisões médicas Human-in-the-Loop."""
    __tablename__ = "trilha_auditoria"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    documento_id = Column(String(100), index=True, nullable=False)
    auditor_nome = Column(String(150), nullable=False)
    decisao = Column(String(50), nullable=False)  # aprovado, rejeitado, corrigido
    justificativa = Column(Text, nullable=False)
    dados_anteriores = Column(JSON, nullable=True)
    dados_finais = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
