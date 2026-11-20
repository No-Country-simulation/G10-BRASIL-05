"""0004 hospitais base schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0004_hospitais_base"
down_revision = "0003_solicitacoes_atendimento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "hospitais" not in tables:
        op.create_table(
            "hospitais",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("nome", sa.String(150), nullable=False, unique=True),
            sa.Column("cnpj", sa.String(30), unique=True),
            sa.Column("cidade", sa.String(100), server_default="São Paulo"),
            sa.Column("uf", sa.String(2), server_default="SP"),
            sa.Column("ativo", sa.Boolean(), server_default=sa.true()),
            sa.Column("created_at", sa.DateTime()),
        )
        op.create_index("ix_hospitais_nome", "hospitais", ["nome"], unique=True)
    else:
        indexes = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("hospitais")}
        if "ix_hospitais_nome" not in indexes:
            op.create_index("ix_hospitais_nome", "hospitais", ["nome"], unique=True)
    indexes = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("hospitais")}
    if "ix_hospitais_id" not in indexes:
        op.create_index("ix_hospitais_id", "hospitais", ["id"])


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
