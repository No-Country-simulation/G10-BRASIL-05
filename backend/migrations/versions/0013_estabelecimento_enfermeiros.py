"""0013 estabelecimento enfermeiros schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0013_estabelecimento_enfermeiros"
down_revision = "0012_estabelecimento_medicos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estabelecimento_enfermeiros",
        sa.Column("estabelecimento_id", sa.Integer(), sa.ForeignKey("estabelecimentos_saude.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("enfermeiro_id", sa.Integer(), sa.ForeignKey("enfermeiros.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("funcao", sa.String(50)),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("inicio_vinculo", sa.DateTime()),
        sa.Column("fim_vinculo", sa.DateTime()),
    )


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
