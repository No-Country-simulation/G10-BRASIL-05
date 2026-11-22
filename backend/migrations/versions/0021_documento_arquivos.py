"""Cria tabela documento_arquivos."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0021_documento_arquivos"
down_revision = "0020_doc_especialidades"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documento_arquivos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("documento_id", sa.Integer(), nullable=False),
        sa.Column("papel", sa.String(length=20), nullable=False),
        sa.Column("bucket", sa.String(length=150), nullable=False),
        sa.Column("caminho_atual", sa.String(length=500), nullable=False),
        sa.Column("hash_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["documento_id"], ["documentos_triagem.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bucket", "caminho_atual", name="uq_documento_arquivo_objeto"),
    )
    op.create_index("ix_documento_arquivos_documento_id", "documento_arquivos", ["documento_id"], unique=False)
    op.create_index("ix_documento_arquivos_hash_sha256", "documento_arquivos", ["hash_sha256"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documento_arquivos_hash_sha256", table_name="documento_arquivos")
    op.drop_index("ix_documento_arquivos_documento_id", table_name="documento_arquivos")
    op.drop_table("documento_arquivos")
