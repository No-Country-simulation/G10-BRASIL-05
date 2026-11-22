"""Cria tabela contatos_whatsapp."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0025_contatos_whatsapp"
down_revision = "0024_revisoes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contatos_whatsapp",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("numero", sa.String(length=30), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero"),
    )


def downgrade() -> None:
    op.drop_table("contatos_whatsapp")
