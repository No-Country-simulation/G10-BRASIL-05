"""Cria tabela estabelecimento_profissionais."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_estab_profissionais"
down_revision = "0011_usuarios_sistema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estabelecimento_profissionais",
        sa.Column("estabelecimento_id", sa.Integer(), nullable=False),
        sa.Column("medico_id", sa.Integer(), nullable=False),
        sa.Column("inicio_vinculo", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fim_vinculo", sa.DateTime(timezone=True), nullable=True),
        sa.Column("funcao", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["estabelecimento_id"], ["estabelecimentos_saude.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["medico_id"], ["medicos.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("estabelecimento_id", "medico_id", "inicio_vinculo"),
    )


def downgrade() -> None:
    op.drop_table("estabelecimento_profissionais")
