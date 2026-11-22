"""Cria tabela especialidades."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_especialidades"
down_revision = "0005_clinicas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "especialidades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome"),
    )


def downgrade() -> None:
    op.drop_table("especialidades")
