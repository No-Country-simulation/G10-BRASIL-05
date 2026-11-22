"""Cria tabela revisoes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0024_revisoes"
down_revision = "0023_encaminhamentos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revisoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("documento_id", sa.Integer(), nullable=False),
        sa.Column("revisor_id", sa.Integer(), nullable=False),
        sa.Column("decisao", sa.String(length=30), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("revisado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["documento_id"], ["documentos_triagem.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["revisor_id"], ["usuarios_sistema.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_revisoes_documento_id", "revisoes", ["documento_id"], unique=False)
    op.create_index("ix_revisoes_revisor_id", "revisoes", ["revisor_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_revisoes_revisor_id", table_name="revisoes")
    op.drop_index("ix_revisoes_documento_id", table_name="revisoes")
    op.drop_table("revisoes")
