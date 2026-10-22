from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DocumentoTriagemModel(Base):
    """Tabela principal de armazenamento de triagens clínicas processadas."""
    __tablename__ = "documentos_triagem"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    documento_id = Column(String(100), unique=True, index=True, nullable=False)
    tipo_arquivo = Column(String(50), nullable=False)
    canal_origem = Column(String(100), default="Pronto_Socorro")
    documento_texto = Column(Text, nullable=True)

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
