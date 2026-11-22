"""Cria tabela estabelecimentos_saude."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_estab_saude"
down_revision = "0001_cidades"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estabelecimentos_saude",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("nome", sa.String(length=180), nullable=False),
        sa.Column("cnpj", sa.String(length=30), nullable=True),
        sa.Column("logradouro", sa.String(length=180), nullable=True),
        sa.Column("numero", sa.String(length=30), nullable=True),
        sa.Column("complemento", sa.String(length=120), nullable=True),
        sa.Column("bairro", sa.String(length=100), nullable=True),
        sa.Column("cep", sa.String(length=12), nullable=True),
        sa.Column("cidade_id", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo IN ('HOSPITAL', 'CLINICA')", name="ck_estabelecimentos_tipo"),
        sa.ForeignKeyConstraint(["cidade_id"], ["cidades.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cnpj"),
    )
    op.create_index("ix_estabelecimentos_saude_cidade_id", "estabelecimentos_saude", ["cidade_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_estabelecimentos_saude_cidade_id", table_name="estabelecimentos_saude")
    op.drop_table("estabelecimentos_saude")
