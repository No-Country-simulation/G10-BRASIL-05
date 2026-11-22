"""Cria tabela medico_especialidades."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_med_especialidades"
down_revision = "0007_medicos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "medico_especialidades",
        sa.Column("medico_id", sa.Integer(), nullable=False),
        sa.Column("especialidade_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["especialidade_id"], ["especialidades.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["medico_id"], ["medicos.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("medico_id", "especialidade_id"),
    )


def downgrade() -> None:
    op.drop_table("medico_especialidades")
