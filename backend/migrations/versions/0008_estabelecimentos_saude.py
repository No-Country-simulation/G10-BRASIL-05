"""0008 estabelecimentos saude schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0008_estabelecimentos_saude"
down_revision = "0007_enfermeiros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estabelecimentos_saude",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(180), nullable=False),
        sa.Column("cnpj", sa.String(30), unique=True),
        sa.Column("logradouro", sa.String(180)),
        sa.Column("numero", sa.String(30)),
        sa.Column("complemento", sa.String(120)),
        sa.Column("bairro", sa.String(100)),
        sa.Column("cidade", sa.String(100), nullable=False),
        sa.Column("uf", sa.String(2), nullable=False),
        sa.Column("cep", sa.String(12)),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("tipo IN ('HOSPITAL', 'CLINICA')", name="ck_estab_tipo"),
    )
    op.create_index("ix_estabelecimentos_saude_nome", "estabelecimentos_saude", ["nome"])


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
