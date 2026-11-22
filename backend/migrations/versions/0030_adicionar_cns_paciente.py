"""Adiciona coluna cns na tabela pacientes."""
from alembic import op
import sqlalchemy as sa

revision = "0030_adicionar_cns_paciente"
down_revision = "0029_seed_dados_iniciais"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pacientes", sa.Column("cns", sa.String(length=15), nullable=True))
    op.create_index(op.f("ix_pacientes_cns"), "pacientes", ["cns"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pacientes_cns"), table_name="pacientes")
    op.drop_column("pacientes", "cns")
