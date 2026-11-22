"""Cria tabela instancias_whatsapp."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0026_instancias_whatsapp"
down_revision = "0025_contatos_whatsapp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instancias_whatsapp",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_name", sa.String(length=100), nullable=False),
        sa.Column("status_conexao", sa.String(length=50), server_default=sa.text("'close'"), nullable=False),
        sa.Column("numero_conectado", sa.String(length=30), nullable=True),
        sa.Column("webhook_url", sa.String(length=500), nullable=True),
        sa.Column("gerenciado_por_usuario_id", sa.Integer(), nullable=True),
        sa.Column("gerenciado_por_email_configurado", sa.String(length=150), nullable=True),
        sa.Column("modo_operacao", sa.String(length=50), server_default=sa.text("'AGENTE_AUTONOMO_UNICO'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gerenciado_por_usuario_id"], ["usuarios_sistema.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instance_name"),
    )


def downgrade() -> None:
    op.drop_table("instancias_whatsapp")
