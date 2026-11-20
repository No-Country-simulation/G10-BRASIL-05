"""0007 enfermeiros schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0007_enfermeiros"
down_revision = "0006_pacientes_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enfermeiros",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("coren", sa.String(30), nullable=False, unique=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("area_atuacao", sa.String(100)),
        sa.Column("uf", sa.String(2)),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_enfermeiros_coren", "enfermeiros", ["coren"], unique=True)


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
