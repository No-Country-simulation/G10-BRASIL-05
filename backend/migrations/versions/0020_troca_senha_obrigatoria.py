"""Add mandatory password rotation flag to system users."""

from alembic import op
import sqlalchemy as sa


revision = "0020_troca_senha_obrigatoria"
down_revision = "0019_encaminhamentos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios_sistema",
        sa.Column(
            "trocar_senha_obrigatorio",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("usuarios_sistema", "trocar_senha_obrigatorio", server_default=None)


def downgrade() -> None:
    op.drop_column("usuarios_sistema", "trocar_senha_obrigatorio")
