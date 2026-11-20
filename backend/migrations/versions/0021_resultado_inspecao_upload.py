"""Persiste inspeção prévia do arquivo nos resultados de triagem."""

from alembic import op
import sqlalchemy as sa


revision = "0021_resultado_inspecao_upload"
down_revision = "0020_troca_senha_obrigatoria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documentos_triagem", sa.Column("metadados_documento", sa.JSON(), nullable=True))
    op.add_column("documentos_triagem", sa.Column("campos_rotulados", sa.JSON(), nullable=True))
    op.add_column("documentos_triagem", sa.Column("escopo_documento", sa.String(length=30), nullable=True))
    op.add_column("documentos_triagem", sa.Column("legibilidade_documento", sa.String(length=30), nullable=True))
    op.add_column("documentos_triagem", sa.Column("evidencias_escopo", sa.JSON(), nullable=True))
    op.add_column("documentos_triagem", sa.Column("justificativa_escopo", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documentos_triagem", "justificativa_escopo")
    op.drop_column("documentos_triagem", "evidencias_escopo")
    op.drop_column("documentos_triagem", "legibilidade_documento")
    op.drop_column("documentos_triagem", "escopo_documento")
    op.drop_column("documentos_triagem", "campos_rotulados")
    op.drop_column("documentos_triagem", "metadados_documento")
