"""0018 destinos roteamento schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0018_destinos_roteamento"
down_revision = "0017_atendimento_enfermeiros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destinos_roteamento",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(50), nullable=False, unique=True),
        sa.Column("tipo", sa.String(25), nullable=False),
        sa.Column("estabelecimento_id", sa.Integer(), sa.ForeignKey("estabelecimentos_saude.id")),
        sa.Column("descricao", sa.String(250)),
        sa.CheckConstraint("tipo IN ('FILA', 'ESTABELECIMENTO')", name="ck_destino_tipo"),
    )
    op.bulk_insert(
        sa.table("destinos_roteamento", sa.column("codigo", sa.String), sa.column("tipo", sa.String), sa.column("descricao", sa.String)),
        [
            {"codigo": "FARMACIA", "tipo": "FILA", "descricao": "Destino genérico; o paciente escolhe a farmácia."},
            {"codigo": "AUDITORIA", "tipo": "FILA", "descricao": "Fila de auditoria humana."},
            {"codigo": "EMERGENCIA", "tipo": "FILA", "descricao": "Fila de emergência médica."},
            {"codigo": "FLUXO_PADRAO", "tipo": "FILA", "descricao": "Fluxo padrão de atendimento."},
        ],
    )


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
