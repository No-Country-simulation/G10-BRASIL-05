"""Cria tabela hospital_diretores."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_hospital_diretores"
down_revision = "0013_estab_enfermeiros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hospital_diretores",
        sa.Column("hospital_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("inicio_vinculo", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fim_vinculo", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitais.estabelecimento_id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios_sistema.id"], ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.PrimaryKeyConstraint("hospital_id", "usuario_id", "inicio_vinculo"),
    )


def downgrade() -> None:
    op.drop_table("hospital_diretores")
