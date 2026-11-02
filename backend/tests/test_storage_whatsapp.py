import os
import pytest
from app.repositories.storage import StorageRepository


def test_sanitizar_nome_arquivo():
    """Valida normalização e remoção de caracteres perigosos ou acentuados."""
    assert StorageRepository.sanitizar_nome_arquivo("Laudo Tomografia Tórax.PDF") == "laudo_tomografia_torax"
    assert StorageRepository.sanitizar_nome_arquivo("Receita médica Dr. João #123.jpg") == "receita_medica_dr_joao_123"
    assert StorageRepository.sanitizar_nome_arquivo("!!!____teste...arquivo--ok???.png") == "teste_arquivo--ok"
    assert StorageRepository.sanitizar_nome_arquivo("") == "documento_clinico"
    assert StorageRepository.sanitizar_nome_arquivo(None) == "documento_clinico"


def test_gerar_nome_arquivo_whatsapp():
    """Valida geração de nome padronizado para mensagens WhatsApp com timestamp e ID."""
    repo = StorageRepository()
    nome = repo.gerar_nome_arquivo_whatsapp(
        documento_id="DOC-WPP-TEST-001",
        nome_original="Exame Sangue.pdf",
        extensao=".pdf",
    )
    assert nome.startswith("WPP_DOC-WPP-TEST-001_")
    assert nome.endswith("_exame_sangue.pdf")


def test_salvar_arquivo_whatsapp_cria_arquivo_em_storage(tmp_path):
    """Valida persistência física do arquivo binário na pasta Storage com nome renomeado."""
    repo = StorageRepository(local_storage_dir=str(tmp_path))
    conteudo_teste = b"%PDF-1.4 Fake PDF Content for Clinical Triage"

    resultado = repo.salvar_arquivo_whatsapp(
        documento_id="DOC-WPP-9988",
        conteudo=conteudo_teste,
        nome_original="Laudo Clínico Urgente.pdf",
        extensao=".pdf",
        mimetype="application/pdf",
    )

    assert resultado["status_backup"] == "sucesso_local"
    assert resultado["tamanho_bytes"] == len(conteudo_teste)
    assert os.path.exists(resultado["caminho_local"])

    with open(resultado["caminho_local"], "rb") as f:
        gravado = f.read()

    assert gravado == conteudo_teste
    assert resultado["nome_arquivo"].startswith("WPP_DOC-WPP-9988_")
    assert resultado["nome_arquivo"].endswith("_laudo_clinico_urgente.pdf")


def test_salvar_triagem_json_cria_json_em_storage(tmp_path):
    """Valida que o JSON de triagem é persistido na pasta local Storage/processados."""
    repo = StorageRepository(local_storage_dir=str(tmp_path))
    dados = {"documento_id": "DOC-JSON-001", "status": "processado"}

    resultado = repo.salvar_triagem_json(
        documento_id="DOC-JSON-001",
        dados_resultado=dados,
        is_urgente=True,
    )

    caminho_esperado = os.path.join(str(tmp_path), "processados/urgentes/DOC-JSON-001.json")
    assert os.path.exists(caminho_esperado)
    assert resultado["status_backup"] == "sucesso (local_simulado)"
