"""Cria tabela atendimento_enfermeiros."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017_atend_enfermeiros"
down_revision = "0016_atend_profissionais"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "atendimento_enfermeiros",
        sa.Column("atendimento_id", sa.Integer(), nullable=False),
        sa.Column("enfermeiro_id", sa.Integer(), nullable=False),
        sa.Column("funcao", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["atendimento_id"], ["atendimentos.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["enfermeiro_id"], ["enfermeiros.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("atendimento_id", "enfermeiro_id"),
    )


def downgrade() -> None:
    op.drop_table("atendimento_enfermeiros")
