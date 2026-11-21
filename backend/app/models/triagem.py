"""Modelos relacionais MediFlow alinhados ao esquema PostgreSQL V4.

Conteúdo clínico variável e eventos de auditoria vivem no MongoDB. Esta base
mantém somente estado operacional e relações usadas para garantir integridade.
"""

from typing import Any
from datetime import date
from uuid import uuid4

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index,
    Integer, JSON, Numeric, String, Table, Text, UniqueConstraint, Uuid,
    func, text,
)
from sqlalchemy.orm import declarative_base, relationship, synonym, validates
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

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


class UsuarioSistemaModel(Base):
    __tablename__ = "usuarios_sistema"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(150), nullable=False, unique=True)
    nome = Column(String(150), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    papel = Column(String(50), nullable=False, default="SOMENTE_LEITURA", server_default="SOMENTE_LEITURA")
    # Metadados do perfil de acesso preservam os valores das seeds; não substituem
    # os registros normalizados em medicos/enfermeiros.
    registro = Column(String(80))
    especialidade = Column(String(150))
    trocar_senha_obrigatorio = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    medico_id = Column(Integer, ForeignKey("medicos.id", ondelete="RESTRICT", onupdate="RESTRICT"))
    enfermeiro_id = Column(Integer, ForeignKey("enfermeiros.id", ondelete="RESTRICT", onupdate="RESTRICT"))
    pode_gerenciar_whatsapp = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    ativo = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    medico = relationship("MedicoModel")
    enfermeiro = relationship("EnfermeiroModel")

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


class AtendimentoModel(Base):
    __tablename__ = "atendimentos"
    __table_args__ = (
        UniqueConstraint("id", "paciente_id", name="uq_atendimentos_id_paciente"),
        UniqueConstraint("id", "estabelecimento_id", name="uq_atendimentos_id_estabelecimento"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False, index=True)
    estabelecimento_id = Column(Integer, ForeignKey("estabelecimentos_saude.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False, index=True)
    data_atendimento = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(String(30), nullable=False, default="ABERTO", server_default="ABERTO")


class AtendimentoProfissionalModel(Base):
    __tablename__ = "atendimento_profissionais"
    atendimento_id = Column(Integer, ForeignKey("atendimentos.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    medico_id = Column(Integer, ForeignKey("medicos.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    funcao = Column(String(50))


class AtendimentoEnfermeiroModel(Base):
    __tablename__ = "atendimento_enfermeiros"
    atendimento_id = Column(Integer, ForeignKey("atendimentos.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    enfermeiro_id = Column(Integer, ForeignKey("enfermeiros.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    funcao = Column(String(50))


class DestinoRoteamentoModel(Base):
    __tablename__ = "destinos_roteamento"
    __table_args__ = (
        CheckConstraint("tipo IN ('FILA', 'ESTABELECIMENTO')", name="ck_destino_tipo"),
        CheckConstraint("(tipo = 'ESTABELECIMENTO') = (estabelecimento_id IS NOT NULL)", name="ck_destino_estabelecimento"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(50), nullable=False, unique=True)
    tipo = Column(String(25), nullable=False)
    estabelecimento_id = Column(Integer, ForeignKey("estabelecimentos_saude.id", ondelete="RESTRICT", onupdate="RESTRICT"))
    descricao = Column(String(250))


class DocumentoTriagemModel(Base):
    __tablename__ = "documentos_triagem"
    __table_args__ = (
        ForeignKeyConstraint(
            ["atendimento_id", "paciente_id"],
            ["atendimentos.id", "atendimentos.paciente_id"],
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["atendimento_id", "estabelecimento_id"],
            ["atendimentos.id", "atendimentos.estabelecimento_id"],
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        UniqueConstraint("id", "atendimento_id", name="uq_documentos_id_atendimento"),
        CheckConstraint("score_confianca IS NULL OR score_confianca BETWEEN 0 AND 1", name="ck_documento_score"),
        CheckConstraint(
            "status_processamento IN ('RECEBIDO','EM_PROCESSAMENTO','PENDENTE_IDENTIFICACAO','EM_REVISAO_HUMANA','ROTEADO','CONCLUIDO','REJEITADO','ERRO','AGUARDANDO_REENVIO')",
            name="ck_documento_status",
        ),
        CheckConstraint("status_processamento <> 'CONCLUIDO' OR (paciente_id IS NOT NULL AND estabelecimento_id IS NOT NULL)", name="ck_documento_concluido_identificado"),
        CheckConstraint("atendimento_id IS NULL OR (paciente_id IS NOT NULL AND estabelecimento_id IS NOT NULL)", name="ck_documento_atendimento_identificado"),
        CheckConstraint("status_processamento NOT IN ('ROTEADO','CONCLUIDO') OR destino_id IS NOT NULL", name="ck_documento_destino_final"),
        Index("ix_documentos_revisao_fila", "created_at", postgresql_where=text("status_processamento = 'EM_REVISAO_HUMANA'")),
        Index("ix_documentos_status_created", "status_processamento", "created_at"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column("documento_externo_id", String(100), nullable=False, unique=True)
    tipo_arquivo = Column(String(50), nullable=False)
    canal_origem = Column(String(100))
    paciente_id = Column(Integer, ForeignKey("pacientes.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    estabelecimento_id = Column(Integer, ForeignKey("estabelecimentos_saude.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    atendimento_id = Column(Integer, index=True)
    tipo_documento = Column(String(100))
    cid_principal = Column(String(10))
    nivel_prioridade = Column(String(50), nullable=False, default="Indefinida", server_default="Indefinida")
    score_confianca = Column(Numeric(5, 4))
    destino_id = Column(Integer, ForeignKey("destinos_roteamento.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    status_processamento = Column(String(30), nullable=False, default="RECEBIDO", server_default="RECEBIDO")
    versao = Column(Integer, nullable=False, default=0, server_default="0")
    ultima_sequencia = Column(Integer, nullable=False, default=0, server_default="0")
    mongo_audit_stream_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid4)
    whatsapp_numero = Column(String(30))
    whatsapp_nome = Column(String(150))
    whatsapp_message_id = Column(String(150), index=True)
    hash_sha256 = Column(String(64))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    paciente = relationship("PacienteModel", back_populates="documentos")
    medico = relationship("MedicoModel", back_populates="documentos")
    estabelecimento = relationship("EstabelecimentoSaudeModel")
    atendimento = relationship(
        "AtendimentoModel",
        foreign_keys=[atendimento_id],
        primaryjoin="DocumentoTriagemModel.atendimento_id == AtendimentoModel.id",
    )
    destino = relationship("DestinoRoteamentoModel")
    especialidades = relationship("EspecialidadeModel", secondary="documento_especialidades")
    arquivos = relationship("DocumentoArquivoModel", back_populates="documento")

    _payload_fields = {
        "documento_texto", "justificativa_roteamento", "dados_extraidos", "evidencias_campos",
        "metadados_documento", "campos_rotulados", "escopo_documento", "legibilidade_documento",
        "evidencias_escopo", "justificativa_escopo", "motivo_revisao", "etapa_revisao", "caminho_fonte",
    }

    def __init__(self, **kwargs: Any):
        payload = {}
        for key in tuple(kwargs):
            if key in self._payload_fields:
                payload[key] = kwargs.pop(key)
        super().__init__(**kwargs)
        self._clinical_payload = payload

    def get_clinical_payload(self) -> dict[str, Any]:
        return dict(getattr(self, "_clinical_payload", {}) or {})

    def set_clinical_payload(self, payload: dict[str, Any] | None) -> None:
        self._clinical_payload = dict(payload or {})

    @validates("status_processamento")
    def _normalizar_status(self, _key: str, value: str) -> str:
        aliases = {
            "EM_AUDITORIA": "EM_REVISAO_HUMANA",
            "PROCESSADO": "ROTEADO",
            "AUDITORIA_REJEITADO": "REJEITADO",
        }
        status = (value or "RECEBIDO").strip().upper()
        return aliases.get(status, status)

    @property
    def bucket_oci(self) -> str | None:
        return self.get_clinical_payload().get("bucket_oci") or (self.arquivos[0].bucket if self.arquivos else None)

    @bucket_oci.setter
    def bucket_oci(self, value: str | None) -> None:
        payload = self.get_clinical_payload()
        payload["bucket_oci"] = value
        self.set_clinical_payload(payload)

    @property
    def caminho_objeto_oci(self) -> str | None:
        return self.get_clinical_payload().get("caminho_objeto_oci") or (self.arquivos[0].caminho_atual if self.arquivos else None)

    @caminho_objeto_oci.setter
    def caminho_objeto_oci(self, value: str | None) -> None:
        payload = self.get_clinical_payload()
        payload["caminho_objeto_oci"] = value
        self.set_clinical_payload(payload)

    @property
    def hospital_id(self) -> int | None:
        return self.estabelecimento_id

    @hospital_id.setter
    def hospital_id(self, value: int | None) -> None:
        self.estabelecimento_id = value

    @property
    def hospital(self) -> HospitalModel | None:
        return self.estabelecimento.hospital if self.estabelecimento else None

    @property
    def destino_principal(self) -> str | None:
        return getattr(self, "_destino_codigo", None) or (self.destino.codigo if self.destino else None)

    @destino_principal.setter
    def destino_principal(self, value: str | None) -> None:
        self._destino_codigo = value

    @property
    def requer_auditoria_humana(self) -> bool:
        return self.status_processamento in {"EM_REVISAO_HUMANA", "AGUARDANDO_REENVIO"}

    @requer_auditoria_humana.setter
    def requer_auditoria_humana(self, value: bool) -> None:
        if value:
            self.status_processamento = "EM_REVISAO_HUMANA"

    @property
    def especialidade(self) -> str | None:
        nomes = [item.nome for item in self.especialidades]
        return " / ".join(nomes) if nomes else getattr(self, "_especialidade_nome", None)

    @especialidade.setter
    def especialidade(self, value: str | None) -> None:
        self._especialidade_nome = value


def _clinical_payload_property(key: str):
    def getter(instance: DocumentoTriagemModel):
        return instance.get_clinical_payload().get(key)
    def setter(instance: DocumentoTriagemModel, value):
        payload = instance.get_clinical_payload()
        payload[key] = value
        instance.set_clinical_payload(payload)
    return property(getter, setter)


for _payload_key in DocumentoTriagemModel._payload_fields:
    setattr(DocumentoTriagemModel, _payload_key, _clinical_payload_property(_payload_key))


class DocumentoEspecialidadeModel(Base):
    __tablename__ = "documento_especialidades"
    documento_id = Column(Integer, ForeignKey("documentos_triagem.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    especialidade_id = Column(Integer, ForeignKey("especialidades.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)


class DocumentoArquivoModel(Base):
    __tablename__ = "documento_arquivos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey("documentos_triagem.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False, index=True)
    papel = Column(String(20), nullable=False)
    bucket = Column(String(150), nullable=False)
    caminho_atual = Column(String(500), nullable=False)
    hash_sha256 = Column(String(64), index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint("bucket", "caminho_atual", name="uq_documento_arquivo_objeto"),)
    documento = relationship("DocumentoTriagemModel", back_populates="arquivos")


class ArquivoMovimentacaoModel(Base):
    __tablename__ = "arquivo_movimentacoes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    arquivo_id = Column(Integer, ForeignKey("documento_arquivos.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False)
    bucket_origem = Column(String(150))
    caminho_origem = Column(String(500), nullable=False)
    bucket_destino = Column(String(150))
    caminho_destino = Column(String(500), nullable=False)
    motivo = Column(String(60))
    movido_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RevisaoModel(Base):
    __tablename__ = "revisoes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey("documentos_triagem.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False, index=True)
    revisor_id = Column(Integer, ForeignKey("usuarios_sistema.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False, index=True)
    decisao = Column(String(30), nullable=False)
    observacao = Column(Text)
    revisado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ContatoWhatsAppModel(Base):
    __tablename__ = "contatos_whatsapp"
    id = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(String(30), nullable=False, unique=True)
    nome = Column(String(150))


class InstanciaWhatsAppModel(Base):
    __tablename__ = "instancias_whatsapp"
    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_name = Column(String(100), nullable=False, unique=True)
    status_conexao = Column(String(50), nullable=False, default="close", server_default="close")
    numero_conectado = Column(String(30))
    webhook_url = Column(String(500))
    gerenciado_por_usuario_id = Column(Integer, ForeignKey("usuarios_sistema.id", ondelete="RESTRICT", onupdate="RESTRICT"))
    gerenciado_por_email_configurado = Column(String(150))
    modo_operacao = Column(String(50), nullable=False, default="AGENTE_AUTONOMO_UNICO", server_default="AGENTE_AUTONOMO_UNICO")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    gerenciado_por = relationship("UsuarioSistemaModel")

    @property
    def conectado(self) -> bool:
        return self.status_conexao.lower() in {"open", "connected", "conectado"}

    @conectado.setter
    def conectado(self, value: bool) -> None:
        if value:
            self.status_conexao = "open"
        elif self.status_conexao.lower() in {"open", "connected", "conectado"}:
            self.status_conexao = "close"

    @property
    def gerenciado_por_email(self) -> str | None:
        return self.gerenciado_por.email if self.gerenciado_por else self.gerenciado_por_email_configurado

    @gerenciado_por_email.setter
    def gerenciado_por_email(self, value: str | None) -> None:
        self.gerenciado_por_email_configurado = value


class DocumentoOrigemWhatsAppModel(Base):
    __tablename__ = "documento_origem_whatsapp"
    __table_args__ = (UniqueConstraint("instancia_id", "message_id", name="uq_whatsapp_instancia_mensagem"),)
    documento_id = Column(Integer, ForeignKey("documentos_triagem.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    contato_id = Column(Integer, ForeignKey("contatos_whatsapp.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False, index=True)
    instancia_id = Column(Integer, ForeignKey("instancias_whatsapp.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False)
    message_id = Column(String(150), nullable=False)


class EncaminhamentoModel(Base):
    __tablename__ = "encaminhamentos"
    __table_args__ = (
        ForeignKeyConstraint(
            ["documento_id", "atendimento_id"],
            ["documentos_triagem.id", "documentos_triagem.atendimento_id"],
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        CheckConstraint("status IN ('SOLICITADO','ACEITO','CONCLUIDO','RECUSADO','CANCELADO')", name="ck_encaminhamento_status"),
        Index("ix_encaminhamentos_destino_status", "destino_id", "status"),
        Index("ix_encaminhamentos_documento_atendimento", "documento_id", "atendimento_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    atendimento_id = Column(Integer, ForeignKey("atendimentos.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False, index=True)
    documento_id = Column(Integer, nullable=False)
    destino_id = Column(Integer, ForeignKey("destinos_roteamento.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False)
    status = Column(String(25), nullable=False, default="SOLICITADO", server_default="SOLICITADO")
    solicitado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    concluido_em = Column(DateTime(timezone=True))
    usuario_responsavel_id = Column(Integer, ForeignKey("usuarios_sistema.id", ondelete="RESTRICT", onupdate="RESTRICT"))
    observacao = Column(Text)


class AuditoriaOutboxModel(Base):
    __tablename__ = "auditoria_outbox"
    __table_args__ = (
        UniqueConstraint("documento_id", "sequencia", name="uq_outbox_documento_sequencia"),
        CheckConstraint("sequencia > 0", name="ck_outbox_sequencia_positiva"),
        CheckConstraint("tentativas >= 0", name="ck_outbox_tentativas_nao_negativas"),
        CheckConstraint("status IN ('PENDENTE','EM_PUBLICACAO','PUBLICADO','ERRO','ERRO_INTEGRIDADE')", name="ck_outbox_status"),
        Index("ix_outbox_pendente", "criado_em", postgresql_where=text("status = 'PENDENTE'")),
        Index("ix_outbox_stream_sequencia", "documento_id", "sequencia"),
    )
    evento_id = Column(Uuid(as_uuid=True), primary_key=True)
    documento_id = Column(Integer, ForeignKey("documentos_triagem.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False)
    documento_externo_id = Column(String(100), nullable=False)
    sequencia = Column(Integer, nullable=False)
    tipo_evento = Column(String(60), nullable=False)
    ocorrido_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    payload = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="PENDENTE", server_default="PENDENTE")
    tentativas = Column(Integer, nullable=False, default=0, server_default="0")
    claim_token = Column(Uuid(as_uuid=True))
    lease_ate = Column(DateTime(timezone=True))
    proxima_tentativa_em = Column(DateTime(timezone=True))
    erro_ultimo = Column(Text)
    mongo_evento_id = Column(String(100))
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    publicado_em = Column(DateTime(timezone=True))
