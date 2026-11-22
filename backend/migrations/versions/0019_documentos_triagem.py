"""Cria tabela documentos_triagem."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0019_documentos_triagem"
down_revision = "0018_destinos_roteamento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documentos_triagem",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("documento_externo_id", sa.String(length=100), nullable=False),
        sa.Column("tipo_arquivo", sa.String(length=50), nullable=False),
        sa.Column("canal_origem", sa.String(length=100), nullable=True),
        sa.Column("paciente_id", sa.Integer(), nullable=True),
        sa.Column("medico_id", sa.Integer(), nullable=True),
        sa.Column("estabelecimento_id", sa.Integer(), nullable=True),
        sa.Column("atendimento_id", sa.Integer(), nullable=True),
        sa.Column("tipo_documento", sa.String(length=100), nullable=True),
        sa.Column("cid_principal", sa.String(length=10), nullable=True),
        sa.Column("nivel_prioridade", sa.String(length=50), server_default=sa.text("'Indefinida'"), nullable=False),
        sa.Column("score_confianca", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("destino_id", sa.Integer(), nullable=True),
        sa.Column("status_processamento", sa.String(length=30), server_default=sa.text("'RECEBIDO'"), nullable=False),
        sa.Column("versao", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ultima_sequencia", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("mongo_audit_stream_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("whatsapp_numero", sa.String(length=30), nullable=True),
        sa.Column("whatsapp_nome", sa.String(length=150), nullable=True),
        sa.Column("whatsapp_message_id", sa.String(length=150), nullable=True),
        sa.Column("hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("score_confianca IS NULL OR score_confianca BETWEEN 0 AND 1", name="ck_documento_score"),
        sa.CheckConstraint("status_processamento IN ('RECEBIDO','EM_PROCESSAMENTO','PENDENTE_IDENTIFICACAO','EM_REVISAO_HUMANA','ROTEADO','CONCLUIDO','REJEITADO','ERRO','AGUARDANDO_REENVIO')", name="ck_documento_status"),
        sa.CheckConstraint("status_processamento <> 'CONCLUIDO' OR (paciente_id IS NOT NULL AND estabelecimento_id IS NOT NULL)", name="ck_documento_concluido_identificado"),
        sa.CheckConstraint("atendimento_id IS NULL OR (paciente_id IS NOT NULL AND estabelecimento_id IS NOT NULL)", name="ck_documento_atendimento_identificado"),
        sa.CheckConstraint("status_processamento NOT IN ('ROTEADO','CONCLUIDO') OR destino_id IS NOT NULL", name="ck_documento_destino_final"),
        sa.ForeignKeyConstraint(["atendimento_id", "estabelecimento_id"], ["atendimentos.id", "atendimentos.estabelecimento_id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["atendimento_id", "paciente_id"], ["atendimentos.id", "atendimentos.paciente_id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["destino_id"], ["destinos_roteamento.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["estabelecimento_id"], ["estabelecimentos_saude.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["medico_id"], ["medicos.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["paciente_id"], ["pacientes.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("documento_externo_id"),
        sa.UniqueConstraint("id", "atendimento_id", name="uq_documentos_id_atendimento"),
        sa.UniqueConstraint("mongo_audit_stream_id"),
    )
    op.create_index("ix_documentos_triagem_medico_id", "documentos_triagem", ["medico_id"], unique=False)
    op.create_index("ix_documentos_triagem_atendimento_id", "documentos_triagem", ["atendimento_id"], unique=False)
    op.create_index("ix_documentos_status_created", "documentos_triagem", ["status_processamento", "created_at"], unique=False)
    op.create_index("ix_documentos_triagem_whatsapp_message_id", "documentos_triagem", ["whatsapp_message_id"], unique=False)
    op.create_index("ix_documentos_revisao_fila", "documentos_triagem", ["created_at"], unique=False, postgresql_where=sa.text("status_processamento = 'EM_REVISAO_HUMANA'"))
    op.create_index("ix_documentos_triagem_paciente_id", "documentos_triagem", ["paciente_id"], unique=False)
    op.create_index("ix_documentos_triagem_estabelecimento_id", "documentos_triagem", ["estabelecimento_id"], unique=False)
    op.create_index("ix_documentos_triagem_destino_id", "documentos_triagem", ["destino_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documentos_triagem_destino_id", table_name="documentos_triagem")
    op.drop_index("ix_documentos_triagem_estabelecimento_id", table_name="documentos_triagem")
    op.drop_index("ix_documentos_triagem_paciente_id", table_name="documentos_triagem")
    op.drop_index("ix_documentos_revisao_fila", table_name="documentos_triagem", postgresql_where=sa.text("status_processamento = 'EM_REVISAO_HUMANA'"))
    op.drop_index("ix_documentos_triagem_whatsapp_message_id", table_name="documentos_triagem")
    op.drop_index("ix_documentos_status_created", table_name="documentos_triagem")
    op.drop_index("ix_documentos_triagem_atendimento_id", table_name="documentos_triagem")
    op.drop_index("ix_documentos_triagem_medico_id", table_name="documentos_triagem")
    op.drop_table("documentos_triagem")
