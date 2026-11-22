"""Cria tabela arquivo_movimentacoes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0022_arquivo_movimentacoes"
down_revision = "0021_documento_arquivos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "arquivo_movimentacoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("arquivo_id", sa.Integer(), nullable=False),
        sa.Column("bucket_origem", sa.String(length=150), nullable=True),
        sa.Column("caminho_origem", sa.String(length=500), nullable=False),
        sa.Column("bucket_destino", sa.String(length=150), nullable=True),
        sa.Column("caminho_destino", sa.String(length=500), nullable=False),
        sa.Column("motivo", sa.String(length=60), nullable=True),
        sa.Column("movido_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["arquivo_id"], ["documento_arquivos.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("arquivo_movimentacoes")
