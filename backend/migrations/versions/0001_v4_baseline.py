"""Cria o esquema relacional MediFlow V4.

Revision ID: 0001_v4_baseline
Revises:
"""
from alembic import op

from app.models.triagem import Base


revision = "0001_v4_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline do banco descartável após reset local; alterações futuras devem
    # ser migrations explícitas, sem depender do estado atual dos modelos.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
