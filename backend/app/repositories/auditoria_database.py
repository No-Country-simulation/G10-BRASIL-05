from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.triagem import DocumentoTriagemModel, RevisaoModel, UsuarioSistemaModel
from app.repositories.documentos import DocumentosRepository
from app.repositories.nosql_auditoria import MongoAuditoriaRepository
from app.config.logger import logger

class AuditoriaDatabaseRepository:
    """Lista a fila de revisão e registra decisões de auditoria."""

    def __init__(self, db: Session, documentos: DocumentosRepository):
        self.db = db
        self.documentos = documentos

    def listar_auditoria(self) -> List[DocumentoTriagemModel]:
        """Retorna documentos que aguardam revisão humana."""
        documentos = (
            self.db.query(DocumentoTriagemModel)
            .filter(DocumentoTriagemModel.status_processamento == "EM_REVISAO_HUMANA")
            .order_by(DocumentoTriagemModel.created_at.desc())
            .all()
        )
        mongo = None
        try:
            mongo = MongoAuditoriaRepository()
            for documento in documentos:
                self.documentos.hidratar_payload_clinico(documento, mongo)
        except Exception:
            logger.exception("Não foi possível carregar os payloads clínicos da fila pelo Mongo.")
        finally:
            if mongo is not None:
                mongo.fechar()
        return documentos

    def registrar_decisao(
        self,
        documento_id: str,
        decisao: str,
        auditor_nome: str,
        justificativa: str,
        dados_corrigidos: Optional[Dict[str, Any]] = None,
        revisor_id: int | None = None,
    ) -> Optional[DocumentoTriagemModel]:
        documento = self.documentos.buscar_por_documento_id(documento_id)
        if not documento:
            return None

        consulta_revisor = self.db.query(UsuarioSistemaModel).filter_by(ativo=True)
        revisor = (
            consulta_revisor.filter_by(id=revisor_id).first()
            if revisor_id is not None
            else consulta_revisor.filter_by(nome=auditor_nome).first()
        )
        if revisor is None:
            raise ValueError("O revisor autenticado não foi encontrado no cadastro de usuários.")
        self.db.add(
            RevisaoModel(
                documento_id=documento.id,
                revisor_id=revisor.id,
                decisao=decisao,
                observacao=justificativa,
            )
        )
        status_por_decisao = {
            "aprovado": "ROTEADO",
            "corrigido": "ROTEADO",
            "rejeitado": "REJEITADO",
            "solicitar_reenvio": "AGUARDANDO_REENVIO",
        }
        documento.status_processamento = status_por_decisao.get(decisao.lower(), "EM_REVISAO_HUMANA")
        if dados_corrigidos:
            documento.dados_extraidos = dados_corrigidos

        self.db.flush()
        return documento
