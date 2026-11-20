"""0012 estabelecimento medicos schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0012_estabelecimento_medicos"
down_revision = "0011_clinicas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estabelecimento_profissionais",
        sa.Column("estabelecimento_id", sa.Integer(), sa.ForeignKey("estabelecimentos_saude.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("medico_id", sa.Integer(), sa.ForeignKey("medicos.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("funcao", sa.String(50)),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("inicio_vinculo", sa.DateTime()),
        sa.Column("fim_vinculo", sa.DateTime()),
    )


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
