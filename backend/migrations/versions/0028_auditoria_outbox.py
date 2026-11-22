"""Cria tabela auditoria_outbox."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0028_auditoria_outbox"
down_revision = "0027_doc_origem_whatsapp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auditoria_outbox",
        sa.Column("evento_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("documento_id", sa.Integer(), nullable=False),
        sa.Column("documento_externo_id", sa.String(length=100), nullable=False),
        sa.Column("sequencia", sa.Integer(), nullable=False),
        sa.Column("tipo_evento", sa.String(length=60), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'PENDENTE'"), nullable=False),
        sa.Column("tentativas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("claim_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_ate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proxima_tentativa_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("erro_ultimo", sa.Text(), nullable=True),
        sa.Column("mongo_evento_id", sa.String(length=100), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("sequencia > 0", name="ck_outbox_sequencia_positiva"),
        sa.CheckConstraint("tentativas >= 0", name="ck_outbox_tentativas_nao_negativas"),
        sa.CheckConstraint("status IN ('PENDENTE','EM_PUBLICACAO','PUBLICADO','ERRO','ERRO_INTEGRIDADE')", name="ck_outbox_status"),
        sa.ForeignKeyConstraint(["documento_id"], ["documentos_triagem.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("evento_id"),
        sa.UniqueConstraint("documento_id", "sequencia", name="uq_outbox_documento_sequencia"),
    )
    op.create_index("ix_outbox_stream_sequencia", "auditoria_outbox", ["documento_id", "sequencia"], unique=False)
    op.create_index("ix_outbox_pendente", "auditoria_outbox", ["criado_em"], unique=False, postgresql_where=sa.text("status = 'PENDENTE'"))


def downgrade() -> None:
    op.drop_index("ix_outbox_pendente", table_name="auditoria_outbox", postgresql_where=sa.text("status = 'PENDENTE'"))
    op.drop_index("ix_outbox_stream_sequencia", table_name="auditoria_outbox")
    op.drop_table("auditoria_outbox")
