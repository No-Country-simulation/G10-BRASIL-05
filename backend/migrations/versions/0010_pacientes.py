"""Cria tabela pacientes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_pacientes"
down_revision = "0009_enfermeiros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pacientes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cpf", sa.String(length=20), nullable=True),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("cadastro_provisorio", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cpf"),
    )


def downgrade() -> None:
    op.drop_table("pacientes")
