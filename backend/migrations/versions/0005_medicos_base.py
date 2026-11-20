"""0005 medicos base schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0005_medicos_base"
down_revision = "0004_hospitais_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "medicos" not in tables:
        op.create_table(
            "medicos",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("crm", sa.String(30), nullable=False, unique=True),
            sa.Column("nome", sa.String(150), nullable=False),
            sa.Column("especialidade", sa.String(100), server_default="Clínica Médica"),
            sa.Column("uf", sa.String(2), server_default="SP"),
            sa.Column("created_at", sa.DateTime()),
        )
    indexes = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("medicos")}
    if "ix_medicos_crm" not in indexes:
        op.create_index("ix_medicos_crm", "medicos", ["crm"], unique=True)
    if "ix_medicos_id" not in indexes:
        op.create_index("ix_medicos_id", "medicos", ["id"])


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
