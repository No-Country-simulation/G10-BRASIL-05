"""0016 atendimento medicos schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0016_atendimento_medicos"
down_revision = "0015_atendimentos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "atendimento_profissionais",
        sa.Column("atendimento_id", sa.Integer(), sa.ForeignKey("atendimentos.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("medico_id", sa.Integer(), sa.ForeignKey("medicos.id"), primary_key=True),
        sa.Column("funcao", sa.String(50)),
    )


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
