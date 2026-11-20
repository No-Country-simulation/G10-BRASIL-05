"""0010 hospitais estabelecimento schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0010_hospitais_estabelecimento"
down_revision = "0009_categorias_hospital"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    columns = {c["name"] for c in inspector.get_columns("hospitais")}
    if "estabelecimento_id" not in columns:
        with op.batch_alter_table("hospitais") as batch:
            batch.add_column(sa.Column("estabelecimento_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_hospitais_estabelecimento", "estabelecimentos_saude", ["estabelecimento_id"], ["id"])
            batch.create_unique_constraint("uq_hospitais_estabelecimento", ["estabelecimento_id"])
    if "categoria_id" not in columns:
        with op.batch_alter_table("hospitais") as batch:
            batch.add_column(sa.Column("categoria_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_hospitais_categoria", "categorias_hospital", ["categoria_id"], ["id"])
    op.execute(sa.text(
        "INSERT INTO estabelecimentos_saude (tipo, nome, cnpj, cidade, uf, ativo) "
        "SELECT 'HOSPITAL', h.nome, h.cnpj, COALESCE(h.cidade, ''), COALESCE(h.uf, ''), COALESCE(h.ativo, true) "
        "FROM hospitais h WHERE NOT EXISTS (SELECT 1 FROM estabelecimentos_saude e "
        "WHERE e.tipo = 'HOSPITAL' AND e.nome = h.nome)"
    ))
    op.execute(sa.text(
        "UPDATE hospitais SET estabelecimento_id = (SELECT e.id FROM estabelecimentos_saude e "
        "WHERE e.tipo = 'HOSPITAL' AND e.nome = hospitais.nome) WHERE estabelecimento_id IS NULL"
    ))


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
