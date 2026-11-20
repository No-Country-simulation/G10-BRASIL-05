"""0015 atendimentos schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0015_atendimentos"
down_revision = "0014_hospital_diretores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "atendimentos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("paciente_id", sa.Integer(), sa.ForeignKey("pacientes.id"), nullable=False),
        sa.Column("estabelecimento_id", sa.Integer(), sa.ForeignKey("estabelecimentos_saude.id")),
        sa.Column("data_atendimento", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(30), nullable=False, server_default="ABERTO"),
    )
    op.create_index("ix_atendimentos_paciente_id", "atendimentos", ["paciente_id"])


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
