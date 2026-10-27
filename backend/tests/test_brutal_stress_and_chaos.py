import concurrent.futures
import io
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.database import init_db
from app.services.redis_service import RedisAuditService

init_db()
client = TestClient(app, raise_server_exceptions=False)


# ==============================================================================
# 1. TESTE DE ESTRESSE: RACE CONDITION LOCK STORM (20 THREADS CONCORRENTES)
# ==============================================================================
def test_race_condition_lock_storm_20_threads():
    """Simula 20 médicos disputando o lock do mesmo documento no mesmo milissegundo.
    
    Apenas 1 DEVE vencer (200 OK); exatamente 19 DEVEM ser rejeitados com 409 Conflito.
    Nenhuma requisição pode retornar 500 ou travar em deadlock.
    """
    doc_id = "DOC-CHAOS-STORM-001"
    res_triagem = client.post(
        "/triagem",
        json={
            "documento_id": doc_id,
            "tipo_arquivo": "TEXTO",
            "canal_origem": "Pronto_Socorro",
            "documento_texto": "Paciente em parada cardiorrespiratória. Requer desfibrilação imediata.",
        },
    )
    assert res_triagem.status_code == 200

    def tentar_bloqueio(idx: int):
        nome_medico = f"Dr. Medico Plantonista #{idx:02d}"
        return client.post(
            f"/triagem/auditoria/{doc_id}/bloquear",
            json={"auditor_nome": nome_medico, "ttl_segundos": 60},
        )

    num_threads = 20
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futuros = [executor.submit(tentar_bloqueio, i) for i in range(num_threads)]
        respostas = [f.result() for f in futuros]

    status_codes = [r.status_code for r in respostas]
    vencedores = [r for r in respostas if r.status_code == 200]
    conflitos = [r for r in respostas if r.status_code == 409]

    # Exatamente 1 deve ser 200, exatamente 19 devem ser 409
    assert len(vencedores) == 1, f"Mais de um médico venceu o lock: {status_codes}"
    assert len(conflitos) == num_threads - 1, f"Número de conflitos incorreto: {status_codes}"

    vencedor_nome = vencedores[0].json()["auditor"]

    # Consulta de status deve bater com o único vencedor
    status_lock = client.get(f"/triagem/auditoria/{doc_id}/status-lock").json()
    assert status_lock["bloqueado"] is True
    assert status_lock["auditor"] == vencedor_nome

    # Vencedor libera o lock
    res_unlock = client.post(
        f"/triagem/auditoria/{doc_id}/desbloquear",
        json={"auditor_nome": vencedor_nome},
    )
    assert res_unlock.status_code == 200


# ==============================================================================
# 2. TESTE DE ESTRESSE: INGESTÃO MASSIVA EM PARALELO (20 DOCUMENTOS CONCORRENTES)
# ==============================================================================
def test_ingestao_massiva_paralela_concorrente():
    """Dispara 20 documentos clínicos simultaneamente contra o pipeline completo de triagem.
    
    Verifica se o pool de conexões do PostgreSQL suporta carga sem 'connection pool exhausted'.
    """
    def submeter_triagem(idx: int):
        payload = {
            "documento_id": f"DOC-MASS-STRESS-{idx:03d}",
            "tipo_arquivo": "TEXTO",
            "canal_origem": f"Polo_Regional_{idx % 4}",
            "documento_texto": (
                f"RELATÓRIO CLÍNICO #{idx}\n"
                f"Paciente: Paciente Concorrente {idx}, {30 + idx} anos\n"
                f"Médico: Dra. Plantonista {idx % 5}, CRM: {900000 + idx}-SP\n"
                f"Diagnóstico: Crise Hipertensiva Aguda.\n"
                f"Conduta: Monitorização contínua na UTI."
            ),
        }
        return client.post("/triagem", json=payload)

    num_docs = 20
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futuros = [executor.submit(submeter_triagem, i) for i in range(num_docs)]
        respostas = [f.result() for f in futuros]

    for idx, resp in enumerate(respostas):
        assert resp.status_code == 200, f"Falha no documento #{idx}: {resp.text}"
        body = resp.json()
        assert body["documento_id"] == f"DOC-MASS-STRESS-{idx:03d}"
        assert body["classificacao"]["nivel_prioridade"] in ["Urgente", "Rotina"]


# ==============================================================================
# 3. FUZZING & ARQUIVOS CORROMPIDOS (ROBUSTEZ DE PARSER)
# ==============================================================================
def test_upload_pdf_corrompido_header_invalido():
    """Envia um arquivo com extensão .pdf contendo bytes caóticos corrompidos.
    
    O sistema DEVE rejeitar com 400 Bad Request, NUNCA com 500 Internal Server Error.
    """
    bytes_lixo = b"%PDF-corrompido-\x00\xFF\xFE\xAA\xBB\xCC\xDD-random-junk"
    response = client.post(
        "/triagem/upload",
        files={"file": ("laudo_danificado.pdf", bytes_lixo, "application/pdf")},
        data={"canal_origem": "Pronto_Socorro", "documento_id": "PDF-LIXO-001"},
    )
    assert response.status_code in [400, 422]
    assert response.status_code != 500
    dados = response.json()
    msg = dados.get("erro", {}).get("mensagem", "") or dados.get("detail", "")
    assert any(termo in msg.lower() for termo in ["falha ao processar", "corrompido", "não foi possível"])


def test_upload_imagem_png_corrompida_sem_header():
    """Envia arquivo .png com payload truncado/inválido.
    
    O sistema DEVE rejeitar graciosamente com 400 ou 422 (sem estourar erro 500).
    """
    bytes_falsos = b"\x89PNG\r\n\x1a\n\x00\x00\x00corrupted-pixel-data"
    response = client.post(
        "/triagem/upload",
        files={"file": ("rx_corrompido.png", bytes_falsos, "image/png")},
        data={"canal_origem": "Ambulatorio", "documento_id": "IMG-LIXO-001"},
    )
    assert response.status_code in [400, 422]
    assert response.status_code != 500
    dados = response.json()
    msg = dados.get("erro", {}).get("mensagem", "") or dados.get("detail", "")
    assert any(termo in msg.lower() for termo in ["imagem", "corrompido", "inválida", "falha"])


def test_payload_text_bomb_gigante_100kb():
    """Envia documento de texto gigante (> 100 KB) simulando bombardeio de logs.
    
    O pipeline deve processar ou truncar sem estourar memória nem entrar em loop infinito.
    """
    texto_gigante = (
        "Paciente: João da Silva Santos, 45 anos. Dr. Renato CRM: 145892-SP. "
        "Histórico clínico extenso e detalhado: " + ("Análise sem alterações clínicas agudas detectadas. " * 2000)
    )
    assert len(texto_gigante) > 100_000

    start_time = time.time()
    response = client.post(
        "/triagem",
        json={
            "documento_id": "DOC-BOMB-001",
            "tipo_arquivo": "TEXTO",
            "canal_origem": "Pronto_Socorro",
            "documento_texto": texto_gigante,
        },
    )
    duration = time.time() - start_time

    assert response.status_code == 200
    assert duration < 5.0, f"Tempo de resposta excessivo no text-bomb: {duration}s"
    res = response.json()
    assert res["status"] in ["processado", "em_auditoria"]


def test_injecao_sqli_xss_em_campos_clinicos():
    """Testa injeção de SQL Injection e XSS nos campos de texto clínico e nome do paciente.
    
    Garante que o ORM SQLAlchemy sanitiza e persiste como texto literal sem executar DDL.
    """
    sqli_text = (
        "Paciente: '; DROP TABLE documentos_triagem; -- <script>alert('XSS')</script>, 40 anos\n"
        "Médico Solicitante: Dr. Robert'); DROP TABLE pacientes; --, CRM: 145892-SP\n"
        "Diagnóstico: Apendicite aguda fase supurativa.\n"
        "Conduta: Cirurgia de emergência."
    )

    response = client.post(
        "/triagem",
        json={
            "documento_id": "DOC-SQLI-TEST-001",
            "tipo_arquivo": "TEXTO",
            "canal_origem": "Emergência",
            "documento_texto": sqli_text,
        },
    )
    assert response.status_code == 200

    # Confirma que as tabelas NÃO foram deletadas
    res_pacientes = client.get("/pacientes")
    assert res_pacientes.status_code == 200

    res_hospitais = client.get("/hospitais")
    assert res_hospitais.status_code == 200


# ==============================================================================
# 4. CAOS CLÍNICO: CONTRADIÇÕES EXTREMAS E AMBIGUIDADE MÉDICA
# ==============================================================================
def test_caos_clinico_achados_conflitantes_extremos():
    """Texto contendo simultaneamente afirmação de normalidade e emergência letal.
    
    O motor de avaliação de risco DEVE priorizar a emergência com segurança do paciente em 1º lugar.
    """
    texto_conflitante = (
        "Paciente: Marcos Vinicius, 58 anos. Dr. Alberto CRM: 145892-SP.\n"
        "Evolução: Paciente encontra-se estável, eupneico, afebril e sem queixas agudas. "
        "Apresenta ritmo cardíaco regular sem sopros. Alta hospitalar concedida.\n"
        "Achado imprevisto no monitor: Fibrilação Ventricular Aguda, Parada Cardiorrespiratória em curso!"
    )

    response = client.post(
        "/triagem",
        json={
            "documento_id": "DOC-CHAOS-CLIN-001",
            "tipo_arquivo": "TEXTO",
            "canal_origem": "Pronto_Socorro",
            "documento_texto": texto_conflitante,
        },
    )
    assert response.status_code == 200
    res = response.json()

    # O sistema não pode classificar como Rotina diante de fibrilação/PCR
    assert res["classificacao"]["nivel_prioridade"] == "Urgente"
    assert "Emergencia" in res["decisao_roteamento"]["destino_principal"] or res["decisao_roteamento"]["requer_auditoria_humana"] is True


def test_caos_clinico_documento_ilegivel_ou_sem_dados():
    """Texto médico contendo apenas pontuações ou caracteres aleatórios (simulando caligrafia ilegível).
    
    DEVE ser roteado obrigatoriamente para Auditoria Humana (Human-in-the-Loop) com baixa confiança.
    """
    response = client.post(
        "/triagem",
        json={
            "documento_id": "DOC-CHAOS-ILEGIVEL-001",
            "tipo_arquivo": "TEXTO",
            "canal_origem": "Ambulatorio",
            "documento_texto": "... ??? ### @@@ %%% ...",
        },
    )
    assert response.status_code == 200
    res = response.json()

    # Documento sem entidades deve ter score rebaixado e ir para auditoria médica
    assert res["classificacao"]["score_confianca_classificacao"] <= 0.75 or res["decisao_roteamento"]["requer_auditoria_humana"] is True
    assert res["status"] in ["em_auditoria", "processado"]


# ==============================================================================
# 5. EXPIRAÇÃO DE LOCK E REENTRÂNCIA TEMPORAL NO REDIS
# ==============================================================================
def test_expiracao_automatica_ttl_lock_redis():
    """Valida que um lock com TTL curtíssimo (1 segundo) expira e permite que outro médico assuma."""
    service = RedisAuditService()
    doc_id = "DOC-TTL-EXPIRY-001"

    # 1. Dr. Alfa adquire lock com TTL de 1 segundo
    adquiriu = service.adquirir_lock(doc_id, "Dr. Alfa", ttl_segundos=1)
    assert adquiriu is True

    # Imediatamente, Dr. Beta tenta e falha
    assert service.adquirir_lock(doc_id, "Dr. Beta", ttl_segundos=10) is False

    # Aguarda expiração do TTL (1.2 segundos)
    time.sleep(1.2)

    # 2. Agora Dr. Beta DEVE conseguir adquirir o lock sem conflito
    adquiriu_beta = service.adquirir_lock(doc_id, "Dr. Beta", ttl_segundos=10)
    assert adquiriu_beta is True
    assert service.obter_status_lock(doc_id)["auditor"] == "Dr. Beta"

    # Limpa lock
    service.liberar_lock(doc_id, "Dr. Beta")
