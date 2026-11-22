"""Cria tabela atendimento_profissionais."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016_atend_profissionais"
down_revision = "0015_atendimentos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "atendimento_profissionais",
        sa.Column("atendimento_id", sa.Integer(), nullable=False),
        sa.Column("medico_id", sa.Integer(), nullable=False),
        sa.Column("funcao", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["atendimento_id"], ["atendimentos.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["medico_id"], ["medicos.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("atendimento_id", "medico_id"),
    )


def downgrade() -> None:
    op.drop_table("atendimento_profissionais")
