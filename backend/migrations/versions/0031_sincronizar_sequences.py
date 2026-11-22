"""Sincroniza todas as sequences de IDs com os valores maximos das tabelas."""
from alembic import op

revision = "0031_sincronizar_sequences"
down_revision = "0030_adicionar_cns_paciente"
branch_labels = None
depends_on = None

TABELAS = [
    "estabelecimentos_saude",
    "cidades",
    "categorias_hospital",
    "especialidades",
    "medicos",
    "usuarios_sistema",
    "destinos_roteamento",
    "pacientes",
    "documentos_triagem",
]


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        for tabela in TABELAS:
            op.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{tabela}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {tabela}), 1)
                )
                """
            )


def downgrade() -> None:
    pass
