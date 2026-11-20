"""0019 encaminhamentos schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0019_encaminhamentos"
down_revision = "0018_destinos_roteamento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "encaminhamentos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("atendimento_id", sa.Integer(), sa.ForeignKey("atendimentos.id"), nullable=False),
        sa.Column("destino_id", sa.Integer(), sa.ForeignKey("destinos_roteamento.id"), nullable=False),
        sa.Column("status", sa.String(25), nullable=False, server_default="SOLICITADO"),
        sa.Column("solicitado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("concluido_em", sa.DateTime()),
        sa.Column("usuario_responsavel_id", sa.Integer(), sa.ForeignKey("usuarios_sistema.id")),
        sa.Column("observacao", sa.Text()),
        sa.CheckConstraint("status IN ('SOLICITADO', 'ACEITO', 'CONCLUIDO', 'RECUSADO', 'CANCELADO')", name="ck_encaminhamento_status"),
    )
    op.create_index("ix_encaminhamentos_atendimento_id", "encaminhamentos", ["atendimento_id"])


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
