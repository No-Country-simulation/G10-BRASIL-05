"""0006 pacientes base schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0006_pacientes_base"
down_revision = "0005_medicos_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "pacientes" not in tables:
        op.create_table(
            "pacientes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("cpf", sa.String(20), unique=True),
            sa.Column("nome", sa.String(150), nullable=False),
            sa.Column("idade", sa.Integer()),
            sa.Column("cadastro_provisorio", sa.Boolean(), server_default=sa.false()),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )
        op.create_index("ix_pacientes_nome", "pacientes", ["nome"])
    indexes = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("pacientes")}
    if "ix_pacientes_id" not in indexes:
        op.create_index("ix_pacientes_id", "pacientes", ["id"])
    if "ix_pacientes_cpf" not in indexes:
        op.create_index("ix_pacientes_cpf", "pacientes", ["cpf"], unique=True)
    if "ix_pacientes_nome" not in indexes:
        op.create_index("ix_pacientes_nome", "pacientes", ["nome"])


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
