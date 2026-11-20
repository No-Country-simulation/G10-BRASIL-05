"""0017 atendimento enfermeiros schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0017_atendimento_enfermeiros"
down_revision = "0016_atendimento_medicos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "atendimento_enfermeiros",
        sa.Column("atendimento_id", sa.Integer(), sa.ForeignKey("atendimentos.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("enfermeiro_id", sa.Integer(), sa.ForeignKey("enfermeiros.id"), primary_key=True),
        sa.Column("funcao", sa.String(50)),
    )


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
