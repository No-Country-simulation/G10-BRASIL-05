"""Fachada compatível para as consultas e gravações do banco."""

from typing import Any, Dict, List, Optional
from datetime import date

from sqlalchemy.orm import Session

from app.repositories.auditoria_database import AuditoriaDatabaseRepository
from app.models.triagem import (
    DocumentoTriagemModel,
    HospitalModel,
    InstanciaWhatsAppModel,
    MedicoModel,
    PacienteModel,
    UsuarioSistemaModel,
)
from app.repositories.documentos import DocumentosRepository
from app.repositories.hospitais import HospitaisRepository
from app.repositories.medicos import MedicosRepository
from app.repositories.pacientes import PacientesRepository
from app.repositories.usuarios_database import UsuariosDatabaseRepository
from app.repositories.whatsapp_database import (
    EMAIL_INSTITUCIONAL_WHATSAPP,
    InstanciasWhatsAppRepository,
)

class DatabaseRepository:
    """Preserva a API existente e encaminha cada operação ao seu domínio."""

    def __init__(self, db: Session):
        self.db = db
        self._pacientes = PacientesRepository(db)
        self._medicos = MedicosRepository(db)
        self._hospitais = HospitaisRepository(db)
        self._documentos = DocumentosRepository(
            db, self._pacientes, self._medicos, self._hospitais
        )
        self._auditoria = AuditoriaDatabaseRepository(db, self._documentos)
        self._whatsapp = InstanciasWhatsAppRepository(db)
        self._usuarios = UsuariosDatabaseRepository(db)

    def obter_ou_criar_paciente(
        self,
        nome: str,
        idade: Optional[int] = None,
        cpf: Optional[str] = None,
        data_nascimento: Optional[date] = None,
    ) -> Optional[PacienteModel]:
        return self._pacientes.obter_ou_criar_paciente(nome, idade, cpf, data_nascimento)

    def listar_pacientes(self, skip: int = 0, limit: int = 50) -> List[PacienteModel]:
        return self._pacientes.listar_pacientes(skip, limit)

    def buscar_paciente_por_id(self, paciente_id: int) -> Optional[PacienteModel]:
        return self._pacientes.buscar_paciente_por_id(paciente_id)

    def buscar_pacientes_por_nome(self, nome: str) -> List[PacienteModel]:
        return self._pacientes.buscar_por_nome(nome)

    def listar_historico_paciente(self, paciente_id: int) -> List[DocumentoTriagemModel]:
        documentos = self._pacientes.listar_historico_paciente(paciente_id)
        for documento in documentos:
            self._documentos.hidratar_payload_clinico(documento)
        return documentos

    def obter_ou_criar_medico(
        self,
        nome: str,
        crm: str,
        especialidade: Optional[str] = None,
    ) -> MedicoModel:
        return self._medicos.obter_ou_criar_medico(nome, crm, especialidade)

    def listar_medicos(self, skip: int = 0, limit: int = 50) -> List[MedicoModel]:
        return self._medicos.listar_medicos(skip, limit)

    def buscar_medico_por_crm(self, crm: str) -> Optional[MedicoModel]:
        return self._medicos.buscar_por_crm(crm)

    def obter_ou_criar_hospital(self, nome_ou_canal: str) -> HospitalModel:
        return self._hospitais.obter_ou_criar_hospital(nome_ou_canal)

    def listar_hospitais(self) -> List[HospitalModel]:
        return self._hospitais.listar_hospitais()

    def salvar(self, model: DocumentoTriagemModel) -> DocumentoTriagemModel:
        return self._documentos.salvar(model)

    def vincular_destino(self, documento: DocumentoTriagemModel) -> None:
        self._documentos._vincular_destino(documento)

    def buscar_por_documento_id(self, documento_id: str) -> Optional[DocumentoTriagemModel]:
        return self._documentos.buscar_por_documento_id(documento_id)

    def excluir_documento_e_auditoria(self, documento_id: str) -> None:
        return self._documentos.excluir_documento_e_auditoria(documento_id)

    def listar_todos(self, skip: int = 0, limit: int = 50) -> List[DocumentoTriagemModel]:
        return self._documentos.listar_todos(skip, limit)

    def listar_auditoria(self) -> List[DocumentoTriagemModel]:
        return self._auditoria.listar_auditoria()

    def registrar_decisao(
        self,
        documento_id: str,
        decisao: str,
        auditor_nome: str,
        justificativa: str,
        dados_corrigidos: Optional[Dict[str, Any]] = None,
    ) -> Optional[DocumentoTriagemModel]:
        return self._auditoria.registrar_decisao(
            documento_id, decisao, auditor_nome, justificativa, dados_corrigidos
        )

    def garantir_instancia_whatsapp(self) -> InstanciaWhatsAppModel:
        return self._whatsapp.garantir_instancia_whatsapp()

    def buscar_usuario_sistema_por_email(self, email: str) -> Optional[UsuarioSistemaModel]:
        return self._usuarios.buscar_usuario_sistema_por_email(email)

    def obter_ou_criar_instancia_whatsapp(
        self,
        instance_name: Optional[str] = None,
    ) -> InstanciaWhatsAppModel:
        return self._whatsapp.obter_ou_criar_instancia_whatsapp(instance_name)

    def atualizar_estado_instancia_whatsapp(
        self,
        conectado: bool,
        status_conexao: str,
        webhook_url: Optional[str] = None,
        numero_conectado: Optional[str] = None,
        instance_name: Optional[str] = None,
    ) -> InstanciaWhatsAppModel:
        return self._whatsapp.atualizar_estado_instancia_whatsapp(
            conectado, status_conexao, webhook_url, numero_conectado, instance_name
        )
