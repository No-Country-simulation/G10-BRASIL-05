"""Reserved no-op revision required by the following migration."""

revision = "0003_solicitacoes_atendimento"
down_revision = "0002_triage_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
