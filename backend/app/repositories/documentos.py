from typing import List, Optional

from sqlalchemy.orm import Session
from app.config.logger import logger

from app.models.triagem import (
    ArquivoMovimentacaoModel,
    DocumentoArquivoModel,
    DocumentoTriagemModel,
    DestinoRoteamentoModel,
)
from app.repositories.hospitais import HospitaisRepository
from app.repositories.medicos import MedicosRepository
from app.repositories.pacientes import PacientesRepository
from app.repositories.nosql_auditoria import MongoAuditoriaRepository
from app.services.auditoria_outbox import enfileirar_evento

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
        data_nascimento = paciente_info.get("data_nascimento")

        if nome_paciente and not model.paciente_id:
            paciente_obj = self.pacientes.obter_ou_criar_paciente(
                nome=nome_paciente,
                idade=idade_paciente,
                cpf=cpf_paciente,
                data_nascimento=data_nascimento,
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
        self._vincular_destino(model)

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
            existente.estabelecimento_id = model.estabelecimento_id
            existente.destino_id = model.destino_id
            self._sincronizar_arquivo(existente, model)
            self.db.flush()
            self._enfileirar_triagem(existente, model)
            self.db.flush()
            return existente

        self.db.add(model)
        self.db.flush()
        self._sincronizar_arquivo(model, model)
        self.db.flush()
        self._enfileirar_triagem(model, model)
        self.db.flush()
        return model

    def _enfileirar_triagem(self, documento: DocumentoTriagemModel, origem: DocumentoTriagemModel) -> None:
        payload = {
            **origem.get_clinical_payload(),
            "classificacao": {
                "tipo_documento": origem.tipo_documento,
                "especialidade": origem.especialidade,
                "nivel_prioridade": origem.nivel_prioridade,
                "score_confianca": float(origem.score_confianca) if origem.score_confianca is not None else None,
            },
            "destino_principal": origem.destino_principal,
            "canal_origem": origem.canal_origem,
        }
        enfileirar_evento(
            self.db,
            documento=documento,
            tipo_evento="TRIAGEM_INICIAL",
            autor="Sistema_IA",
            payload=payload,
            justificativa=origem.justificativa_roteamento,
        )

    def _vincular_destino(self, documento: DocumentoTriagemModel) -> None:
        codigo = documento.destino_principal
        if not codigo:
            return
        destino = self.db.query(DestinoRoteamentoModel).filter_by(codigo=codigo).one_or_none()
        if destino is None:
            destino = DestinoRoteamentoModel(codigo=codigo, tipo="FILA")
            self.db.add(destino)
            self.db.flush()
        documento.destino_id = destino.id

    def _sincronizar_arquivo(
        self, documento: DocumentoTriagemModel, origem: DocumentoTriagemModel
    ) -> None:
        bucket = origem.bucket_oci
        caminho = origem.caminho_objeto_oci
        if not bucket or not caminho:
            return
        arquivo = next((a for a in documento.arquivos if a.papel == "RESULTADO"), None)
        if arquivo is None:
            arquivo = DocumentoArquivoModel(documento_id=documento.id, papel="RESULTADO")
            documento.arquivos.append(arquivo)
        elif arquivo.id and (arquivo.bucket != bucket or arquivo.caminho_atual != caminho):
            self.db.add(
                ArquivoMovimentacaoModel(
                    arquivo_id=arquivo.id,
                    bucket_origem=arquivo.bucket,
                    caminho_origem=arquivo.caminho_atual,
                    bucket_destino=bucket,
                    caminho_destino=caminho,
                    motivo="ATUALIZACAO_TRIAGEM",
                )
            )
        arquivo.bucket = bucket
        arquivo.caminho_atual = caminho
        arquivo.hash_sha256 = documento.hash_sha256

    def buscar_por_documento_id(self, documento_id: str) -> Optional[DocumentoTriagemModel]:
        documento = self.db.query(DocumentoTriagemModel).filter(
            DocumentoTriagemModel.documento_id == documento_id
        ).first()
        if documento:
            self.hidratar_payload_clinico(documento)
        return documento

    def hidratar_payload_clinico(self, documento: DocumentoTriagemModel, mongo=None) -> None:
        """Reconstrói os campos transitórios a partir dos eventos imutáveis no Mongo."""
        mongo_proprio = mongo is None
        try:
            if mongo is None:
                mongo = MongoAuditoriaRepository()
            payload = documento.get_clinical_payload()
            for evento in mongo.listar_por_documento(documento.documento_id):
                dados = evento.get("payload") or {}
                if evento.get("tipo_evento") == "TRIAGEM_INICIAL":
                    # Compatível com o formato antigo e com o envelope novo do outbox.
                    if "dados_extraidos" in dados and "classificacao" in dados:
                        payload.update(dados)
                    else:
                        payload.update(dados)
                elif "dados_extraidos" in dados:
                    payload["dados_extraidos"] = dados["dados_extraidos"]
                if dados.get("status_processamento"):
                    payload["status_processamento"] = dados["status_processamento"]
            documento.set_clinical_payload(payload)
        except Exception:
            logger.exception("Não foi possível hidratar o payload clínico do documento %s pelo Mongo.", documento.documento_id)
        finally:
            if mongo_proprio and mongo is not None:
                mongo.fechar()

    def excluir_documento_e_auditoria(self, documento_id: str) -> None:
        """Preserva a trilha e marca como rejeitado, sem apagar registro clínico/auditável."""
        documento = self.buscar_por_documento_id(documento_id)
        if documento:
            documento.status_processamento = "REJEITADO"
            documento.set_clinical_payload({})

    def listar_todos(self, skip: int = 0, limit: int = 50) -> List[DocumentoTriagemModel]:
        documentos = (
            self.db.query(DocumentoTriagemModel)
            .order_by(DocumentoTriagemModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        mongo = None
        try:
            mongo = MongoAuditoriaRepository()
            for documento in documentos:
                self.hidratar_payload_clinico(documento, mongo)
        except Exception:
            logger.exception("Não foi possível carregar os payloads clínicos do Mongo para a lista.")
        finally:
            if mongo is not None:
                mongo.fechar()
        return documentos
