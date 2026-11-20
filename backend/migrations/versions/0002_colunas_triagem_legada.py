"""Add relational triage columns to databases created before Alembic."""

from alembic import op
import sqlalchemy as sa


revision = "0002_triage_columns"
down_revision = "0001_auth_credentials"
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
        ("paciente_id", sa.Integer(), "pacientes"),
        ("medico_id", sa.Integer(), "medicos"),
        ("hospital_id", sa.Integer(), "hospitais"),
        ("evidencias_campos", sa.JSON(), None),
        ("motivo_revisao", sa.Text(), None),
        ("etapa_revisao", sa.String(length=50), None),
        ("caminho_fonte", sa.String(length=500), None),
        ("whatsapp_numero", sa.String(length=30), None),
        ("whatsapp_nome", sa.String(length=150), None),
        ("whatsapp_message_id", sa.String(length=150), None),
    )

    with op.batch_alter_table("documentos_triagem") as tabela:
        for nome, tipo, tabela_referenciada in colunas:
            if nome in colunas_existentes:
                continue
            argumentos = [tipo]
            if tabela_referenciada and tabela_referenciada in tabelas:
                argumentos.append(
                    sa.ForeignKey(
                        f"{tabela_referenciada}.id",
                        name=f"fk_documentos_triagem_{nome}_{tabela_referenciada}",
                    )
                )
            tabela.add_column(sa.Column(nome, *argumentos, nullable=True))


def downgrade() -> None:
    # As colunas podem conter dados em bases legadas; não as removemos automaticamente.
    pass
