import json
from types import SimpleNamespace

import oci
import pytest

from app.config.settings import settings
from app.repositories.arquivos_oci import ArquivosOCIRepository


class ClienteOCIFalso:
    """Substitui o ObjectStorageClient para testar sem acessar a nuvem."""

    def __init__(self):
        self.objetos = {}
        self.fora_do_ar = False

    def _verificar_conexao(self):
        if self.fora_do_ar:
            raise ConnectionError("OCI fora do ar")

    def put_object(self, namespace_name, bucket_name, object_name, put_object_body, content_type, **kwargs):
        self._verificar_conexao()
        self.objetos[object_name] = {"conteudo": put_object_body, "content_type": content_type}

    def get_object(self, namespace_name, bucket_name, object_name, **kwargs):
        self._verificar_conexao()
        if object_name not in self.objetos:
            raise oci.exceptions.ServiceError(404, "ObjectNotFound", {}, "Objeto não encontrado")
        return SimpleNamespace(data=SimpleNamespace(content=self.objetos[object_name]["conteudo"]))

    def rename_object(self, namespace_name, bucket_name, rename_object_details, **kwargs):
        self._verificar_conexao()
        origem = rename_object_details.source_name
        if origem not in self.objetos:
            raise oci.exceptions.ServiceError(404, "ObjectNotFound", {}, "Objeto não encontrado")
        self.objetos[rename_object_details.new_name] = self.objetos.pop(origem)


@pytest.fixture
def repo_sem_oci(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "OCI_USER_OCID", "")
    return ArquivosOCIRepository(pasta_local=tmp_path)


@pytest.fixture
def repo(repo_sem_oci, monkeypatch):
    monkeypatch.setattr(settings, "OCI_NAMESPACE", "namespace_teste")
    repo_sem_oci.client = ClienteOCIFalso()
    return repo_sem_oci


# --- SCRUM-72: upload e leitura ---

def test_salvar_arquivo_original_vai_para_recebidos(repo):
    resultado = repo.salvar_arquivo_original("DOC-001", b"%PDF-1.4", "Laudo.PDF", "application/pdf")

    assert resultado["caminho_objeto"] == "recebidos/DOC-001.pdf"
    assert resultado["status_backup"] == "sucesso"
    assert repo.client.objetos["recebidos/DOC-001.pdf"] == {
        "conteudo": b"%PDF-1.4",
        "content_type": "application/pdf",
    }


def test_ler_arquivo_retorna_bytes_salvos(repo):
    repo.salvar_arquivo_original("DOC-002", b"imagem", "foto.png", "image/png")

    assert repo.ler_arquivo("recebidos/DOC-002.png") == b"imagem"


def test_ler_triagem_json_retorna_dicionario(repo):
    dados = {"documento_id": "DOC-003", "diagnostico": "Avaliação Clínica"}
    repo.client.objetos["processados/rotina/DOC-003.json"] = {
        "conteudo": json.dumps(dados, ensure_ascii=False).encode("utf-8"),
        "content_type": "application/json",
    }

    assert repo.ler_triagem_json("processados/rotina/DOC-003.json") == dados


def test_ler_arquivo_inexistente_gera_file_not_found(repo):
    with pytest.raises(FileNotFoundError):
        repo.ler_arquivo("recebidos/nao-existe.pdf")


# --- SCRUM-73: roteamento por status ---

@pytest.mark.parametrize(
    "is_urgente, requer_auditoria, destino",
    [
        (True, False, "processados/urgentes/DOC-005.pdf"),
        (False, True, "auditoria_humana/DOC-005.pdf"),
        (True, True, "auditoria_humana/DOC-005.pdf"),
        (False, False, "processados/rotina/DOC-005.pdf"),
    ],
)
def test_mover_por_status_envia_para_pasta_certa(repo, is_urgente, requer_auditoria, destino):
    repo.salvar_arquivo_original("DOC-005", b"%PDF-1.4", "laudo.pdf", "application/pdf")

    resultado = repo.mover_por_status("recebidos/DOC-005.pdf", is_urgente, requer_auditoria)

    assert resultado["caminho_objeto"] == destino
    assert resultado["status_backup"] == "sucesso"
    assert "recebidos/DOC-005.pdf" not in repo.client.objetos
    assert repo.client.objetos[destino]["conteudo"] == b"%PDF-1.4"


@pytest.mark.parametrize("is_urgente, requer_auditoria", [(False, False), (True, False), (False, True)])
def test_nao_classificado_tem_prioridade(repo, is_urgente, requer_auditoria):
    repo.salvar_arquivo_original("DOC-018", b"fatura", "fatura.pdf", "application/pdf")

    resultado = repo.mover_por_status(
        "recebidos/DOC-018.pdf", is_urgente, requer_auditoria, nao_classificado=True
    )

    assert resultado["caminho_objeto"] == "nao_classificados/DOC-018.pdf"
    assert resultado["status_backup"] == "sucesso"


def test_mover_arquivo_inexistente_retorna_falha(repo):
    resultado = repo.mover_por_status("recebidos/nao-existe.pdf", is_urgente=True)

    assert resultado["status_backup"].startswith("falha")
    assert resultado["caminho_objeto"] == "recebidos/nao-existe.pdf"


# --- SCRUM-74: modo local (sem credenciais OCI) ---

def test_sem_oci_upload_salva_na_pasta_local(repo_sem_oci, tmp_path):
    resultado = repo_sem_oci.salvar_arquivo_original("DOC-004", b"x", "doc.txt", "text/plain")

    assert resultado["status_backup"] == "sucesso (local)"
    assert (tmp_path / "recebidos" / "DOC-004.txt").read_bytes() == b"x"


def test_sem_oci_leitura_vem_da_pasta_local(repo_sem_oci):
    repo_sem_oci.salvar_arquivo_original("DOC-006", b"conteudo", "doc.txt", "text/plain")

    assert repo_sem_oci.ler_arquivo("recebidos/DOC-006.txt") == b"conteudo"


def test_sem_oci_leitura_inexistente_gera_file_not_found(repo_sem_oci):
    with pytest.raises(FileNotFoundError):
        repo_sem_oci.ler_arquivo("recebidos/nao-existe.txt")


def test_sem_oci_mover_na_pasta_local(repo_sem_oci, tmp_path):
    repo_sem_oci.salvar_arquivo_original("DOC-007", b"x", "doc.txt", "text/plain")

    resultado = repo_sem_oci.mover_por_status("recebidos/DOC-007.txt", is_urgente=True)

    assert resultado["caminho_objeto"] == "processados/urgentes/DOC-007.txt"
    assert resultado["status_backup"] == "sucesso (local)"
    assert not (tmp_path / "recebidos" / "DOC-007.txt").exists()
    assert (tmp_path / "processados" / "urgentes" / "DOC-007.txt").read_bytes() == b"x"


def test_sem_oci_mover_inexistente_retorna_falha(repo_sem_oci):
    resultado = repo_sem_oci.mover_por_status("recebidos/nao-existe.txt")

    assert resultado["status_backup"].startswith("falha")


def test_caminho_que_sai_da_pasta_local_e_bloqueado(repo_sem_oci):
    with pytest.raises(ValueError):
        repo_sem_oci.ler_arquivo("../../segredo.txt")


# --- SCRUM-74: OCI configurada, mas fora do ar ---

def test_oci_fora_do_ar_upload_salva_local(repo, tmp_path):
    repo.client.fora_do_ar = True

    resultado = repo.salvar_arquivo_original("DOC-008", b"laudo", "laudo.pdf", "application/pdf")

    assert resultado["status_backup"] == "falha_oci (salvo_local)"
    assert (tmp_path / "recebidos" / "DOC-008.pdf").read_bytes() == b"laudo"


def test_oci_fora_do_ar_leitura_usa_copia_local(repo):
    repo.client.fora_do_ar = True
    repo.salvar_arquivo_original("DOC-009", b"laudo", "laudo.pdf", "application/pdf")

    assert repo.ler_arquivo("recebidos/DOC-009.pdf") == b"laudo"


def test_oci_fora_do_ar_mover_usa_pasta_local(repo, tmp_path):
    repo.client.fora_do_ar = True
    repo.salvar_arquivo_original("DOC-010", b"laudo", "laudo.pdf", "application/pdf")

    resultado = repo.mover_por_status("recebidos/DOC-010.pdf", requer_auditoria=True)

    assert resultado["status_backup"] == "sucesso (local)"
    assert (tmp_path / "auditoria_humana" / "DOC-010.pdf").exists()


def test_oci_fora_do_ar_sem_copia_local_gera_erro(repo):
    repo.client.fora_do_ar = True

    with pytest.raises(ConnectionError):
        repo.ler_arquivo("recebidos/nao-existe.pdf")


def test_chamadas_oci_usam_retry(repo, monkeypatch):
    chamadas = {}

    def put_object_espiao(**kwargs):
        chamadas.update(kwargs)

    monkeypatch.setattr(repo.client, "put_object", put_object_espiao)
    repo.salvar_arquivo_original("DOC-011", b"x", "doc.txt")

    assert chamadas["retry_strategy"] is oci.retry.DEFAULT_RETRY_STRATEGY


# --- SCRUM-74: sincronizar o que ficou local por falha ---

def test_falha_oci_marca_arquivo_como_pendente(repo):
    repo.client.fora_do_ar = True
    repo.salvar_arquivo_original("DOC-012", b"laudo", "laudo.pdf", "application/pdf")

    assert repo._ler_pendentes() == {"recebidos/DOC-012.pdf": "application/pdf"}


def test_modo_desenvolvimento_nao_gera_pendente(repo_sem_oci):
    repo_sem_oci.salvar_arquivo_original("DOC-013", b"x", "doc.txt", "text/plain")

    assert repo_sem_oci._ler_pendentes() == {}


def test_mover_local_atualiza_pendente(repo):
    repo.client.fora_do_ar = True
    repo.salvar_arquivo_original("DOC-014", b"laudo", "laudo.pdf", "application/pdf")

    repo.mover_por_status("recebidos/DOC-014.pdf", is_urgente=True)

    assert repo._ler_pendentes() == {"processados/urgentes/DOC-014.pdf": "application/pdf"}


def test_sincronizar_envia_para_oci_e_apaga_local(repo, tmp_path):
    repo.client.fora_do_ar = True
    repo.salvar_arquivo_original("DOC-015", b"laudo", "laudo.pdf", "application/pdf")
    repo.mover_por_status("recebidos/DOC-015.pdf", requer_auditoria=True)

    repo.client.fora_do_ar = False
    resultado = repo.sincronizar_pendentes()

    assert resultado == {"enviados": ["auditoria_humana/DOC-015.pdf"], "falhas": []}
    assert repo.client.objetos["auditoria_humana/DOC-015.pdf"] == {
        "conteudo": b"laudo",
        "content_type": "application/pdf",
    }
    assert not (tmp_path / "auditoria_humana" / "DOC-015.pdf").exists()
    assert repo._ler_pendentes() == {}


def test_sincronizar_com_oci_ainda_fora_mantem_pendente(repo, tmp_path):
    repo.client.fora_do_ar = True
    repo.salvar_arquivo_original("DOC-016", b"laudo", "laudo.pdf", "application/pdf")

    resultado = repo.sincronizar_pendentes()

    assert resultado == {"enviados": [], "falhas": ["recebidos/DOC-016.pdf"]}
    assert (tmp_path / "recebidos" / "DOC-016.pdf").exists()
    assert repo._ler_pendentes() == {"recebidos/DOC-016.pdf": "application/pdf"}


def test_sincronizar_sem_oci_nao_envia_nada(repo_sem_oci):
    repo_sem_oci._gravar_pendentes({"recebidos/DOC-017.pdf": "application/pdf"})

    resultado = repo_sem_oci.sincronizar_pendentes()

    assert resultado == {"enviados": [], "falhas": ["recebidos/DOC-017.pdf"]}
