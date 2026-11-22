"""Cria tabela clinicas."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_clinicas"
down_revision = "0004_hospitais"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinicas",
        sa.Column("estabelecimento_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["estabelecimento_id"], ["estabelecimentos_saude.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("estabelecimento_id"),
    )


def downgrade() -> None:
    op.drop_table("clinicas")
