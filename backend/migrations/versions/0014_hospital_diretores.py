"""0014 hospital diretores schema change."""

from alembic import op
import sqlalchemy as sa


revision = "0014_hospital_diretores"
down_revision = "0013_estabelecimento_enfermeiros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hospital_diretores",
        sa.Column("hospital_id", sa.Integer(), sa.ForeignKey("hospitais.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios_sistema.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("inicio_vinculo", sa.DateTime()),
        sa.Column("fim_vinculo", sa.DateTime()),
    )


def downgrade() -> None:
    # These healthcare records may contain operational data; preserve them.
    pass
