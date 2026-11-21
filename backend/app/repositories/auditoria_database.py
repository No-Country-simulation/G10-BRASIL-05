from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.triagem import DocumentoTriagemModel, RevisaoModel, UsuarioSistemaModel
from app.repositories.documentos import DocumentosRepository

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
        for documento in documentos:
            self.documentos.hidratar_payload_clinico(documento)
        return documentos

    def registrar_decisao(
        self,
        documento_id: str,
        decisao: str,
        auditor_nome: str,
        justificativa: str,
        dados_corrigidos: Optional[Dict[str, Any]] = None,
    ) -> Optional[DocumentoTriagemModel]:
        documento = self.documentos.buscar_por_documento_id(documento_id)
        if not documento:
            return None

        revisor = self.db.query(UsuarioSistemaModel).filter_by(nome=auditor_nome, ativo=True).first()
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
