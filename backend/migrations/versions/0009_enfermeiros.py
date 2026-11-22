"""Cria tabela enfermeiros."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_enfermeiros"
down_revision = "0008_med_especialidades"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enfermeiros",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("coren", sa.String(length=30), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("area_atuacao", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("coren", "uf", name="uq_enfermeiros_coren_uf"),
    )


def downgrade() -> None:
    op.drop_table("enfermeiros")
