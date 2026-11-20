from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.triagem import DocumentoTriagemModel, TrilhaAuditoriaModel
from app.repositories.hospitais import HospitaisRepository
from app.repositories.medicos import MedicosRepository
from app.repositories.pacientes import PacientesRepository

class DocumentosRepository:
    """Salva e consulta documentos de triagem."""

    def __init__(
        self,
        db: Session,
        pacientes: PacientesRepository,
        medicos: MedicosRepository,
        hospitais: HospitaisRepository,
    ):
        self.db = db
        self.pacientes = pacientes
        self.medicos = medicos
        self.hospitais = hospitais

    def salvar(self, model: DocumentoTriagemModel) -> DocumentoTriagemModel:
        """Salva a triagem associando automaticamente as entidades relacionais (Upsert)."""
        dados = model.dados_extraidos or {}

        # 1. Vincula Paciente
        paciente_info = dados.get("paciente") or {}
        nome_paciente = paciente_info.get("nome")
        idade_paciente = paciente_info.get("idade")
        cpf_paciente = paciente_info.get("cpf")

        if nome_paciente and not model.paciente_id:
            paciente_obj = self.pacientes.obter_ou_criar_paciente(
                nome=nome_paciente,
                idade=idade_paciente,
                cpf=cpf_paciente,
            )
            if paciente_obj is not None:
                model.paciente_id = paciente_obj.id

        # 2. Vincula Médico Solicitante
        medico_info = dados.get("medico_solicitante") or {}
        crm_medico = medico_info.get("crm")
        nome_medico = medico_info.get("nome")
        if crm_medico and not model.medico_id:
            medico_obj = self.medicos.obter_ou_criar_medico(
                nome=nome_medico or "Médico Solicitante",
                crm=crm_medico,
                especialidade=model.especialidade,
            )
            model.medico_id = medico_obj.id

        # 3. Vincula Unidade Hospitalar
        if model.canal_origem and not model.hospital_id:
            hospital_obj = self.hospitais.obter_ou_criar_hospital(model.canal_origem)
            model.hospital_id = hospital_obj.id

        existente = self.buscar_por_documento_id(model.documento_id)
        if existente:
            existente.tipo_arquivo = model.tipo_arquivo
            existente.canal_origem = model.canal_origem
            existente.documento_texto = model.documento_texto
            existente.tipo_documento = model.tipo_documento
            existente.especialidade = model.especialidade
            existente.nivel_prioridade = model.nivel_prioridade
            existente.score_confianca = model.score_confianca
            existente.destino_principal = model.destino_principal
            existente.requer_auditoria_humana = model.requer_auditoria_humana
            existente.status_processamento = model.status_processamento
            existente.justificativa_roteamento = model.justificativa_roteamento
            existente.dados_extraidos = model.dados_extraidos
            existente.evidencias_campos = model.evidencias_campos
            existente.metadados_documento = model.metadados_documento
            existente.campos_rotulados = model.campos_rotulados
            existente.escopo_documento = model.escopo_documento
            existente.legibilidade_documento = model.legibilidade_documento
            existente.evidencias_escopo = model.evidencias_escopo
            existente.justificativa_escopo = model.justificativa_escopo
            existente.motivo_revisao = model.motivo_revisao
            existente.etapa_revisao = model.etapa_revisao
            existente.caminho_fonte = model.caminho_fonte
            existente.bucket_oci = model.bucket_oci
            existente.caminho_objeto_oci = model.caminho_objeto_oci
            existente.whatsapp_numero = model.whatsapp_numero or existente.whatsapp_numero
            existente.whatsapp_nome = model.whatsapp_nome or existente.whatsapp_nome
            existente.whatsapp_message_id = (
                model.whatsapp_message_id or existente.whatsapp_message_id
            )
            existente.paciente_id = model.paciente_id
            existente.medico_id = model.medico_id
            existente.hospital_id = model.hospital_id
            self.db.flush()
            return existente

        self.db.add(model)
        self.db.flush()
        return model

    def buscar_por_documento_id(self, documento_id: str) -> Optional[DocumentoTriagemModel]:
        return self.db.query(DocumentoTriagemModel).filter(
            DocumentoTriagemModel.documento_id == documento_id
        ).first()

    def excluir_documento_e_auditoria(self, documento_id: str) -> None:
        """Remove conteúdo e metadados de um arquivo que a revisão marcou como fora de escopo."""
        self.db.query(TrilhaAuditoriaModel).filter(
            TrilhaAuditoriaModel.documento_id == documento_id
        ).delete(synchronize_session=False)
        self.db.query(DocumentoTriagemModel).filter(
            DocumentoTriagemModel.documento_id == documento_id
        ).delete(synchronize_session=False)
        self.db.commit()

    def listar_todos(self, skip: int = 0, limit: int = 50) -> List[DocumentoTriagemModel]:
        return (
            self.db.query(DocumentoTriagemModel)
            .order_by(DocumentoTriagemModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
