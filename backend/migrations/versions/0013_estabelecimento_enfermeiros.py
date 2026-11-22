"""Cria tabela estabelecimento_enfermeiros."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_estab_enfermeiros"
down_revision = "0012_estab_profissionais"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estabelecimento_enfermeiros",
        sa.Column("estabelecimento_id", sa.Integer(), nullable=False),
        sa.Column("enfermeiro_id", sa.Integer(), nullable=False),
        sa.Column("inicio_vinculo", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fim_vinculo", sa.DateTime(timezone=True), nullable=True),
        sa.Column("funcao", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["enfermeiro_id"], ["enfermeiros.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["estabelecimento_id"], ["estabelecimentos_saude.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("estabelecimento_id", "enfermeiro_id", "inicio_vinculo"),
    )


def downgrade() -> None:
    op.drop_table("estabelecimento_enfermeiros")
