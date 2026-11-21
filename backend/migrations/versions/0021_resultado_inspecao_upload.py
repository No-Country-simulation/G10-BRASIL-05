"""Persiste inspeção prévia do arquivo nos resultados de triagem."""

from alembic import op
import sqlalchemy as sa


revision = "0021_resultado_inspecao_upload"
down_revision = "0020_troca_senha_obrigatoria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tabelas = set(sa.inspect(bind).get_table_names())
    if "documentos_triagem" not in tabelas:
        return

    colunas_existentes = {
        coluna["name"] for coluna in sa.inspect(bind).get_columns("documentos_triagem")
    }
    colunas = (
        ("metadados_documento", sa.JSON()),
        ("campos_rotulados", sa.JSON()),
        ("escopo_documento", sa.String(length=30)),
        ("legibilidade_documento", sa.String(length=30)),
        ("evidencias_escopo", sa.JSON()),
        ("justificativa_escopo", sa.Text()),
    )
    with op.batch_alter_table("documentos_triagem") as tabela:
        for nome, tipo in colunas:
            if nome not in colunas_existentes:
                tabela.add_column(sa.Column(nome, tipo, nullable=True))


def downgrade() -> None:
    op.drop_column("documentos_triagem", "justificativa_escopo")
    op.drop_column("documentos_triagem", "evidencias_escopo")
    op.drop_column("documentos_triagem", "legibilidade_documento")
    op.drop_column("documentos_triagem", "escopo_documento")
    op.drop_column("documentos_triagem", "campos_rotulados")
    op.drop_column("documentos_triagem", "metadados_documento")
