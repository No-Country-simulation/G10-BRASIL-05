"""Add account profile fields and disable pre-existing shared-salt credentials."""

from alembic import op
import sqlalchemy as sa


revision = "0001_auth_credentials"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "usuarios_sistema" not in inspector.get_table_names():
        op.create_table(
            "usuarios_sistema",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("email", sa.String(length=150), nullable=False),
            sa.Column("nome", sa.String(length=150), nullable=False),
            sa.Column("senha_hash", sa.String(length=255), nullable=False),
            sa.Column("papel", sa.String(length=50), nullable=False, server_default="INSTITUCIONAL_WHATSAPP"),
            sa.Column("registro", sa.String(length=100), nullable=True),
            sa.Column("especialidade", sa.String(length=150), nullable=True),
            sa.Column("pode_gerenciar_whatsapp", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_usuarios_sistema_email", "usuarios_sistema", ["email"], unique=True)
    else:
        colunas = {coluna["name"] for coluna in inspector.get_columns("usuarios_sistema")}
        if "registro" not in colunas:
            op.add_column("usuarios_sistema", sa.Column("registro", sa.String(length=100), nullable=True))
        if "especialidade" not in colunas:
            op.add_column("usuarios_sistema", sa.Column("especialidade", sa.String(length=150), nullable=True))

    # Legacy hashes used a shared salt; all legacy credentials require secure reprovisioning.
    op.execute(
        sa.text(
            "UPDATE usuarios_sistema SET ativo = false, senha_hash = :disabled "
            "WHERE senha_hash NOT LIKE 'pbkdf2_sha256$%'"
        ).bindparams(
            disabled="disabled$rotate-credential",
        )
    )


def downgrade() -> None:
    # Credential invalidation is intentionally irreversible; do not restore the old shared password.
    pass
