"""Cria tabela categorias_hospital."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_categorias_hosp"
down_revision = "0002_estab_saude"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categorias_hospital",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=80), nullable=False),
        sa.Column("descricao", sa.String(length=250), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome"),
    )


def downgrade() -> None:
    op.drop_table("categorias_hospital")
