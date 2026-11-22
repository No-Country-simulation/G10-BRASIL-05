"""Cria tabela medicos."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_medicos"
down_revision = "0006_especialidades"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "medicos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("crm", sa.String(length=30), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crm", "uf", name="uq_medicos_crm_uf"),
    )


def downgrade() -> None:
    op.drop_table("medicos")
