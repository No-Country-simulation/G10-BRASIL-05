"""Cria tabela atendimentos."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015_atendimentos"
down_revision = "0014_hospital_diretores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "atendimentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("paciente_id", sa.Integer(), nullable=False),
        sa.Column("estabelecimento_id", sa.Integer(), nullable=False),
        sa.Column("data_atendimento", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ABERTO'"), nullable=False),
        sa.ForeignKeyConstraint(["estabelecimento_id"], ["estabelecimentos_saude.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["paciente_id"], ["pacientes.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "paciente_id", name="uq_atendimentos_id_paciente"),
        sa.UniqueConstraint("id", "estabelecimento_id", name="uq_atendimentos_id_estabelecimento"),
    )
    op.create_index("ix_atendimentos_paciente_id", "atendimentos", ["paciente_id"], unique=False)
    op.create_index("ix_atendimentos_estabelecimento_id", "atendimentos", ["estabelecimento_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_atendimentos_estabelecimento_id", table_name="atendimentos")
    op.drop_index("ix_atendimentos_paciente_id", table_name="atendimentos")
    op.drop_table("atendimentos")
