"""Cria tabela usuarios_sistema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_usuarios_sistema"
down_revision = "0010_pacientes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios_sistema",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("papel", sa.String(length=50), server_default=sa.text("'SOMENTE_LEITURA'"), nullable=False),
        sa.Column("registro", sa.String(length=80), nullable=True),
        sa.Column("especialidade", sa.String(length=150), nullable=True),
        sa.Column("trocar_senha_obrigatorio", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("medico_id", sa.Integer(), nullable=True),
        sa.Column("enfermeiro_id", sa.Integer(), nullable=True),
        sa.Column("pode_gerenciar_whatsapp", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["enfermeiro_id"], ["enfermeiros.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["medico_id"], ["medicos.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )


def downgrade() -> None:
    op.drop_table("usuarios_sistema")
