"""Cria tabela cidades."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_cidades"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cidades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome", "uf", name="uq_cidades_nome_uf"),
    )


def downgrade() -> None:
    op.drop_table("cidades")
