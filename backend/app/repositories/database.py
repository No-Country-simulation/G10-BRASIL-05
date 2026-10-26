from typing import Generator, List, Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config.settings import settings
from app.models.triagem import Base, DocumentoTriagemModel, TrilhaAuditoriaModel

# Engine com pool seguro; suporte a SQLite em memória como fallback para testes locais
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True if "sqlite" not in settings.DATABASE_URL else False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Cria as tabelas no banco de dados se não existirem."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependência FastAPI para injeção de sessão do banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseRepository:
    """Repositório de persistência para triagens clínicas e auditoria."""

    def __init__(self, db: Session):
        self.db = db

    def salvar(self, model: DocumentoTriagemModel) -> DocumentoTriagemModel:
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def buscar_por_documento_id(self, documento_id: str) -> Optional[DocumentoTriagemModel]:
        return self.db.query(DocumentoTriagemModel).filter(
            DocumentoTriagemModel.documento_id == documento_id
        ).first()

    def listar_todos(self, skip: int = 0, limit: int = 50) -> List[DocumentoTriagemModel]:
        return self.db.query(DocumentoTriagemModel).order_by(
            DocumentoTriagemModel.created_at.desc()
        ).offset(skip).limit(limit).all()

    def listar_auditoria(self) -> List[DocumentoTriagemModel]:
        """Retorna apenas documentos que requerem auditoria humana pendente."""
        return self.db.query(DocumentoTriagemModel).filter(
            DocumentoTriagemModel.requer_auditoria_humana == True,
            DocumentoTriagemModel.status_processamento == "em_auditoria",
        ).order_by(DocumentoTriagemModel.created_at.desc()).all()

    def registrar_decisao(
        self,
        documento_id: str,
        decisao: str,
        auditor_nome: str,
        justificativa: str,
        dados_corrigidos: Optional[Dict[str, Any]] = None,
    ) -> Optional[DocumentoTriagemModel]:
        doc = self.buscar_por_documento_id(documento_id)
        if not doc:
            return None

        # Trilha de auditoria
        trilha = TrilhaAuditoriaModel(
            documento_id=documento_id,
            auditor_nome=auditor_nome,
            decisao=decisao,
            justificativa=justificativa,
            dados_anteriores=doc.dados_extraidos,
            dados_finais=dados_corrigidos or doc.dados_extraidos,
        )
        self.db.add(trilha)

        # Atualiza status do documento
        doc.status_processamento = f"auditoria_{decisao}"
        doc.requer_auditoria_humana = False
        if dados_corrigidos:
            doc.dados_extraidos = dados_corrigidos

        self.db.commit()
        self.db.refresh(doc)
        return doc
