"""0011 clinicas schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0011_clinicas"
down_revision = "0010_hospitais_estabelecimento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinicas",
        sa.Column("estabelecimento_id", sa.Integer(), sa.ForeignKey("estabelecimentos_saude.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
