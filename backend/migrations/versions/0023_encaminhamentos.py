"""Cria tabela encaminhamentos."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0023_encaminhamentos"
down_revision = "0022_arquivo_movimentacoes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "encaminhamentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("atendimento_id", sa.Integer(), nullable=False),
        sa.Column("documento_id", sa.Integer(), nullable=True),
        sa.Column("destino_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=25), server_default=sa.text("'SOLICITADO'"), nullable=False),
        sa.Column("solicitado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usuario_responsavel_id", sa.Integer(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('SOLICITADO','ACEITO','CONCLUIDO','RECUSADO','CANCELADO')", name="ck_encaminhamento_status"),
        sa.ForeignKeyConstraint(["atendimento_id"], ["atendimentos.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["destino_id"], ["destinos_roteamento.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["documento_id", "atendimento_id"], ["documentos_triagem.id", "documentos_triagem.atendimento_id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_responsavel_id"], ["usuarios_sistema.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_encaminhamentos_documento_atendimento", "encaminhamentos", ["documento_id", "atendimento_id"], unique=False)
    op.create_index("ix_encaminhamentos_atendimento_id", "encaminhamentos", ["atendimento_id"], unique=False)
    op.create_index("ix_encaminhamentos_destino_status", "encaminhamentos", ["destino_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_encaminhamentos_destino_status", table_name="encaminhamentos")
    op.drop_index("ix_encaminhamentos_atendimento_id", table_name="encaminhamentos")
    op.drop_index("ix_encaminhamentos_documento_atendimento", table_name="encaminhamentos")
    op.drop_table("encaminhamentos")
