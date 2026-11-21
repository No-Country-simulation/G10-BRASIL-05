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

    def put_object(self, namespace_name, bucket_name, object_name, put_object_body, content_type):
        self.objetos[object_name] = {"conteudo": put_object_body, "content_type": content_type}

    def get_object(self, namespace_name, bucket_name, object_name):
        if object_name not in self.objetos:
            raise oci.exceptions.ServiceError(404, "ObjectNotFound", {}, "Objeto não encontrado")
        return SimpleNamespace(data=SimpleNamespace(content=self.objetos[object_name]["conteudo"]))


@pytest.fixture
def repo_sem_oci(monkeypatch):
    monkeypatch.setattr(settings, "OCI_USER_OCID", "")
    return ArquivosOCIRepository()


@pytest.fixture
def repo(repo_sem_oci, monkeypatch):
    monkeypatch.setattr(settings, "OCI_NAMESPACE", "namespace_teste")
    repo_sem_oci.client = ClienteOCIFalso()
    return repo_sem_oci


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


def test_sem_oci_upload_e_simulado(repo_sem_oci):
    resultado = repo_sem_oci.salvar_arquivo_original("DOC-004", b"x", "doc.txt", "text/plain")

    assert resultado["status_backup"] == "sucesso (local_simulado)"


def test_sem_oci_leitura_gera_erro_claro(repo_sem_oci):
    with pytest.raises(RuntimeError):
        repo_sem_oci.ler_arquivo("recebidos/DOC-004.txt")
