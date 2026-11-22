"""Cria tabela destinos_roteamento."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0018_destinos_roteamento"
down_revision = "0017_atend_enfermeiros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destinos_roteamento",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("tipo", sa.String(length=25), nullable=False),
        sa.Column("estabelecimento_id", sa.Integer(), nullable=True),
        sa.Column("descricao", sa.String(length=250), nullable=True),
        sa.CheckConstraint("tipo IN ('FILA', 'ESTABELECIMENTO')", name="ck_destino_tipo"),
        sa.CheckConstraint("((tipo = 'ESTABELECIMENTO') = (estabelecimento_id IS NOT NULL))", name="ck_destino_estabelecimento"),
        sa.ForeignKeyConstraint(["estabelecimento_id"], ["estabelecimentos_saude.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )
    op.create_index("ix_destinos_roteamento_estabelecimento_id", "destinos_roteamento", ["estabelecimento_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_destinos_roteamento_estabelecimento_id", table_name="destinos_roteamento")
    op.drop_table("destinos_roteamento")
