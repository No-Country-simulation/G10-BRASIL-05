import secrets
import pytest
from fastapi import HTTPException

from app.models.users import UsuarioSistemaModel
from app.repositories.database import SessionLocal
from app.repositories.medicos_repository import MedicosRepository
from app.repositories.users_repository import UsersRepository
from app.schemas.auth import UsuarioAtualizarRequest, UsuarioProvisionarRequest
from app.services.medicos_service import MedicosService
from app.services.users_service import UsersService


def test_users_repository_crud():
    with SessionLocal() as db:
        repo = UsersRepository(db)
        email = f"test-repo-{secrets.token_hex(4)}@example.org"

        # Criar
        user = repo.criar_usuario(
            email=email,
            nome="Usuário Repositório",
            senha_hash="hash_teste",
            papel="DIRETOR",
            ativo=True,
        )
        assert user.id is not None
        assert user.email == email

        # Buscar por id
        buscado_id = repo.buscar_por_id(user.id)
        assert buscado_id is not None
        assert buscado_id.id == user.id

        # Buscar por email
        buscado_email = repo.buscar_por_email(email.upper())
        assert buscado_email is not None
        assert buscado_email.id == user.id

        # Listar ativos
        ativos = repo.listar_ativos(papel="DIRETOR")
        assert any(u.id == user.id for u in ativos)

        # Salvar
        user.nome = "Nome Alterado"
        repo.salvar(user)
        assert repo.buscar_por_id(user.id).nome == "Nome Alterado"

        # Desativar
        repo.remover_ou_desativar(user.id)
        assert repo.buscar_por_id(user.id).ativo is False


def test_medicos_repository_crud():
    with SessionLocal() as db:
        repo = MedicosRepository(db)
        crm = f"CRM{secrets.randbelow(90000) + 10000}"
        uf = "MG"

        # Criar médico
        medico = repo.criar_medico(
            nome="Dra. Roberta",
            crm=crm,
            uf=uf,
            especialidade="Cardiologia / Pediatria",
        )
        assert medico.id is not None
        assert medico.crm == crm
        assert medico.uf == uf

        # Buscar médico
        buscado = repo.buscar_por_crm_uf(crm, uf)
        assert buscado is not None
        assert buscado.id == medico.id

        # Listar médicos
        lista = repo.listar_medicos(0, 100)
        assert any(m.id == medico.id for m in lista)

        # Criar enfermeiro
        coren = f"COREN{secrets.randbelow(90000) + 10000}"
        enfermeiro = repo.criar_enfermeiro(
            nome="Enf. Lucas",
            coren=coren,
            uf="RJ",
            area_atuacao="UTI",
        )
        assert enfermeiro.id is not None
        assert enfermeiro.coren == coren
        assert enfermeiro.uf == "RJ"

        # Buscar enfermeiro
        buscado_enf = repo.buscar_enfermeiro_por_coren_uf(coren, "RJ")
        assert buscado_enf is not None
        assert buscado_enf.id == enfermeiro.id


def test_medicos_service_provisionar_e_rbac():
    with SessionLocal() as db:
        users_repo = UsersRepository(db)
        medicos_repo = MedicosRepository(db)
        service = MedicosService(users_repo=users_repo, medicos_repo=medicos_repo)

        diretor_ator = UsuarioSistemaModel(id=9991, papel="DIRETOR", email="dir@example.org", nome="Diretor")
        medico_ator = UsuarioSistemaModel(id=9992, papel="MEDICO", email="med@example.org", nome="Médico")

        # 1. Médico não pode provisionar outro médico ou diretor
        req_medico = UsuarioProvisionarRequest(
            nome="Dr. Invalido",
            email=f"med-{secrets.token_hex(4)}@example.org",
            senha=secrets.token_urlsafe(16),
            nivel="MEDICO",
            registro="CRM 123456-SP",
        )
        with pytest.raises(HTTPException) as exc:
            service.provisionar_profissional(req_medico, ator=medico_ator)
        assert exc.value.status_code == 403

        # 2. Diretor provisiona médico com CRM/UF extraído
        crm_num = str(secrets.randbelow(900000) + 100000)
        req_med_valido = UsuarioProvisionarRequest(
            nome="Dr. Valido",
            email=f"med-{secrets.token_hex(4)}@example.org",
            senha=secrets.token_urlsafe(16),
            nivel="MEDICO",
            registro=f"CRM {crm_num}-SP",
            especialidade="Ortopedia",
        )
        resp_med = service.provisionar_profissional(req_med_valido, ator=diretor_ator)
        assert resp_med["nivel"] == "MEDICO"
        assert resp_med["email"] == req_med_valido.email

        # 3. Conflito de CRM/UF duplicado
        with pytest.raises(HTTPException) as exc_crm:
            req_duplicado = UsuarioProvisionarRequest(
                nome="Dr. Outro",
                email=f"med2-{secrets.token_hex(4)}@example.org",
                senha=secrets.token_urlsafe(16),
                nivel="MEDICO",
                registro=f"CRM {crm_num}-SP",
            )
            service.provisionar_profissional(req_duplicado, ator=diretor_ator)
        assert exc_crm.value.status_code == 409

        # 4. Conflito de e-mail duplicado
        with pytest.raises(HTTPException) as exc_email:
            req_email_dup = UsuarioProvisionarRequest(
                nome="Dr. Outro Email",
                email=req_med_valido.email,
                senha=secrets.token_urlsafe(16),
                nivel="MEDICO",
                registro="CRM 999888-RJ",
            )
            service.provisionar_profissional(req_email_dup, ator=diretor_ator)
        assert exc_email.value.status_code == 409

        # 5. Médico provisiona enfermeiro com sucesso
        coren_num = str(secrets.randbelow(900000) + 100000)
        req_enf = UsuarioProvisionarRequest(
            nome="Enf. Valido",
            email=f"enf-{secrets.token_hex(4)}@example.org",
            senha=secrets.token_urlsafe(16),
            nivel="ENFERMEIRO",
            registro=f"COREN-SP {coren_num}",
        )
        resp_enf = service.provisionar_profissional(req_enf, ator=medico_ator)
        assert resp_enf["nivel"] == "ENFERMEIRO"
        assert resp_enf["email"] == req_enf.email


def test_users_service_regras_negocio():
    with SessionLocal() as db:
        users_repo = UsersRepository(db)
        service = UsersService(users_repo=users_repo)

        # Usuário para teste
        u_teste = users_repo.criar_usuario(
            email=f"alvo-{secrets.token_hex(4)}@example.org",
            nome="Alvo Teste",
            senha_hash="hash",
            papel="ENFERMEIRO",
            ativo=True,
        )

        diretor = users_repo.criar_usuario(
            email=f"dir-{secrets.token_hex(4)}@example.org",
            nome="Diretor",
            senha_hash="hash",
            papel="DIRETOR",
            ativo=True,
        )
        medico = users_repo.criar_usuario(
            email=f"med-{secrets.token_hex(4)}@example.org",
            nome="Médico",
            senha_hash="hash",
            papel="MEDICO",
            ativo=True,
        )

        # Médico lista usuários: deve receber apenas enfermeiros
        lista_medico = service.listar_usuarios(ator=medico)
        assert all(item["nivel"] == "ENFERMEIRO" for item in lista_medico)

        # Não pode desativar a própria conta
        with pytest.raises(HTTPException) as exc_self:
            service.desativar_usuario(usuario_id=diretor.id, ator=diretor)
        assert exc_self.value.status_code == 400

        # Médico não pode gerenciar diretor
        u_dir = users_repo.criar_usuario(
            email=f"dir-alvo-{secrets.token_hex(4)}@example.org",
            nome="Diretor Alvo",
            senha_hash="hash",
            papel="DIRETOR",
            ativo=True,
        )
        with pytest.raises(HTTPException) as exc_med_dir:
            service.desativar_usuario(usuario_id=u_dir.id, ator=medico)
        assert exc_med_dir.value.status_code == 403

        # Atualizar usuário com sucesso
        atualizado = service.atualizar_usuario(
            usuario_id=u_teste.id,
            dados=UsuarioAtualizarRequest(nome="Alvo Atualizado"),
            ator=diretor,
        )
        assert atualizado["nome"] == "Alvo Atualizado"

        # Auto-edição de médico e enfermeiro permitida
        atualizado_med = service.atualizar_usuario(
            usuario_id=medico.id,
            dados=UsuarioAtualizarRequest(nome="Médico Nome Novo"),
            ator=medico,
        )
        assert atualizado_med["nome"] == "Médico Nome Novo"

        # Diretor não pode gerenciar outro diretor
        with pytest.raises(HTTPException) as exc_dir_dir:
            service.atualizar_usuario(
                usuario_id=u_dir.id,
                dados=UsuarioAtualizarRequest(nome="Tentativa Inválida"),
                ator=diretor,
            )
        assert exc_dir_dir.value.status_code == 403
