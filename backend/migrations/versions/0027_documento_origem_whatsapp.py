"""Cria tabela documento_origem_whatsapp."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0027_doc_origem_whatsapp"
down_revision = "0026_instancias_whatsapp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documento_origem_whatsapp",
        sa.Column("documento_id", sa.Integer(), nullable=False),
        sa.Column("contato_id", sa.Integer(), nullable=False),
        sa.Column("instancia_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.String(length=150), nullable=False),
        sa.ForeignKeyConstraint(["contato_id"], ["contatos_whatsapp.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["documento_id"], ["documentos_triagem.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["instancia_id"], ["instancias_whatsapp.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("documento_id"),
        sa.UniqueConstraint("instancia_id", "message_id", name="uq_whatsapp_instancia_mensagem"),
    )
    op.create_index("ix_documento_origem_whatsapp_contato_id", "documento_origem_whatsapp", ["contato_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documento_origem_whatsapp_contato_id", table_name="documento_origem_whatsapp")
    op.drop_table("documento_origem_whatsapp")
