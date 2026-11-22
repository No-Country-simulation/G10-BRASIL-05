"""Cria tabela hospitais."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_hospitais"
down_revision = "0003_categorias_hosp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hospitais",
        sa.Column("estabelecimento_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias_hospital.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["estabelecimento_id"], ["estabelecimentos_saude.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("estabelecimento_id"),
    )


def downgrade() -> None:
    op.drop_table("hospitais")
