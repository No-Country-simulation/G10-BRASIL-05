"""Cria tabela documento_especialidades."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0020_doc_especialidades"
down_revision = "0019_documentos_triagem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documento_especialidades",
        sa.Column("documento_id", sa.Integer(), nullable=False),
        sa.Column("especialidade_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["documento_id"], ["documentos_triagem.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["especialidade_id"], ["especialidades.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("documento_id", "especialidade_id"),
    )


def downgrade() -> None:
    op.drop_table("documento_especialidades")
