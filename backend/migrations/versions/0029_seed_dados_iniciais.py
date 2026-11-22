"""Semeia dados iniciais importando os datasets de migrations/seeders/."""
from alembic import op
import sqlalchemy as sa

revision = "0029_seed_dados_iniciais"
down_revision = "0028_auditoria_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from migrations.seeders.cidades import DADOS_CIDADES
    from migrations.seeders.categorias_hospital import DADOS_CATEGORIAS_HOSPITAL
    from migrations.seeders.estabelecimentos import (
        DADOS_ESTABELECIMENTOS_SAUDE,
        DADOS_HOSPITAIS,
        DADOS_CLINICAS,
    )
    from migrations.seeders.especialidades import DADOS_ESPECIALIDADES
    from migrations.seeders.medicos import DADOS_MEDICOS, DADOS_MEDICO_ESPECIALIDADES
    from migrations.seeders.destinos import DADOS_DESTINOS_ROTEAMENTO
    from migrations.seeders.usuarios import obter_dados_usuarios
    from migrations.seeders.whatsapp import DADOS_INSTANCIAS_WHATSAPP

    # 1. Cidades
    t_cidades = sa.table(
        "cidades",
        sa.column("id", sa.Integer),
        sa.column("nome", sa.String),
        sa.column("uf", sa.String),
    )
    op.bulk_insert(t_cidades, DADOS_CIDADES)

    # 2. Categorias Hospital
    t_cat = sa.table(
        "categorias_hospital",
        sa.column("id", sa.Integer),
        sa.column("nome", sa.String),
        sa.column("descricao", sa.String),
    )
    op.bulk_insert(t_cat, DADOS_CATEGORIAS_HOSPITAL)

    # 3. Estabelecimentos de Saúde
    t_estab = sa.table(
        "estabelecimentos_saude",
        sa.column("id", sa.Integer),
        sa.column("tipo", sa.String),
        sa.column("nome", sa.String),
        sa.column("cnpj", sa.String),
        sa.column("cidade_id", sa.Integer),
        sa.column("ativo", sa.Boolean),
    )
    op.bulk_insert(t_estab, DADOS_ESTABELECIMENTOS_SAUDE)

    # 4. Hospitais e Clínicas
    t_hosp = sa.table(
        "hospitais",
        sa.column("estabelecimento_id", sa.Integer),
        sa.column("categoria_id", sa.Integer),
    )
    op.bulk_insert(t_hosp, DADOS_HOSPITAIS)

    t_clin = sa.table(
        "clinicas",
        sa.column("estabelecimento_id", sa.Integer),
    )
    op.bulk_insert(t_clin, DADOS_CLINICAS)

    # 5. Especialidades e Médicos
    t_esp = sa.table(
        "especialidades",
        sa.column("id", sa.Integer),
        sa.column("nome", sa.String),
    )
    op.bulk_insert(t_esp, DADOS_ESPECIALIDADES)

    t_med = sa.table(
        "medicos",
        sa.column("id", sa.Integer),
        sa.column("crm", sa.String),
        sa.column("uf", sa.String),
        sa.column("nome", sa.String),
    )
    op.bulk_insert(t_med, DADOS_MEDICOS)

    t_med_esp = sa.table(
        "medico_especialidades",
        sa.column("medico_id", sa.Integer),
        sa.column("especialidade_id", sa.Integer),
    )
    op.bulk_insert(t_med_esp, DADOS_MEDICO_ESPECIALIDADES)

    # 6. Destinos de Roteamento / Filas
    t_dest = sa.table(
        "destinos_roteamento",
        sa.column("codigo", sa.String),
        sa.column("tipo", sa.String),
        sa.column("descricao", sa.String),
    )
    op.bulk_insert(t_dest, DADOS_DESTINOS_ROTEAMENTO)

    # 7. Usuários do Sistema
    t_usr = sa.table(
        "usuarios_sistema",
        sa.column("email", sa.String),
        sa.column("nome", sa.String),
        sa.column("senha_hash", sa.String),
        sa.column("papel", sa.String),
        sa.column("registro", sa.String),
        sa.column("especialidade", sa.String),
        sa.column("ativo", sa.Boolean),
        sa.column("trocar_senha_obrigatorio", sa.Boolean),
        sa.column("pode_gerenciar_whatsapp", sa.Boolean),
    )
    op.bulk_insert(t_usr, obter_dados_usuarios())

    # 8. Instâncias do WhatsApp
    t_zap = sa.table(
        "instancias_whatsapp",
        sa.column("instance_name", sa.String),
        sa.column("status_conexao", sa.String),
        sa.column("modo_operacao", sa.String),
        sa.column("gerenciado_por_email_configurado", sa.String),
    )
    op.bulk_insert(t_zap, DADOS_INSTANCIAS_WHATSAPP)


def downgrade() -> None:
    op.execute("DELETE FROM instancias_whatsapp;")
    op.execute("DELETE FROM usuarios_sistema;")
    op.execute("DELETE FROM medico_especialidades;")
    op.execute("DELETE FROM especialidades;")
    op.execute("DELETE FROM medicos;")
    op.execute("DELETE FROM destinos_roteamento;")
    op.execute("DELETE FROM clinicas;")
    op.execute("DELETE FROM hospitais;")
    op.execute("DELETE FROM estabelecimentos_saude;")
    op.execute("DELETE FROM categorias_hospital;")
    op.execute("DELETE FROM cidades;")
