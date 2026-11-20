"""0009 categorias hospital schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0009_categorias_hospital"
down_revision = "0008_estabelecimentos_saude"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categorias_hospital",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(80), nullable=False, unique=True),
        sa.Column("descricao", sa.String(250)),
    )


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
