from types import SimpleNamespace
from unittest.mock import Mock

from app.services import triagem as triagem_service
from app.schemas.triagem import DecisaoAuditoriaRequest
from app.services.triagem import TriagemService


def test_servico_serializa_correcao_validada_para_os_repositorios(monkeypatch):
    dados_corrigidos = {
        "cid_sugerido": "I20.0",
        "medico_solicitante": {"crm_uf": "145892-SP"},
    }
    decisao = DecisaoAuditoriaRequest.model_validate(
        {
            "status_aprovacao": "corrigido",
            "auditor_nome": "Dra. Ana Silva",
            "justificativa": "Correção clínica revisada.",
            "dados_corrigidos": dados_corrigidos,
        }
    )
    service = TriagemService.__new__(TriagemService)
    service.db_repo = Mock()
    service.db_repo.buscar_por_documento_id.return_value = SimpleNamespace(
        whatsapp_numero=None
    )
    service.db_repo.registrar_decisao.return_value = SimpleNamespace(
        status_processamento="em_auditoria",
        requer_auditoria_humana=True,
        tipo_documento="LAUDO",
        especialidade="Clínica Médica",
        nivel_prioridade="ROTINA",
        score_confianca=0.9,
        destino_principal="Auditoria_Humana",
        justificativa_roteamento="",
        dados_extraidos={},
        motivo_revisao=None,
        etapa_revisao=None,
        evidencias_campos={},
    )
    service.db_repo.db = Mock()
    service.redis_service = Mock()
    service.nosql_repo = Mock()
    monkeypatch.setattr(
        triagem_service,
        "retomar_agente_triagem",
        lambda _documento_id, _decisao: {"status": "validado"},
    )

    service.registrar_decisao_medica("DOC-1", decisao)

    esperado = decisao.dados_corrigidos.model_dump()
    service.db_repo.registrar_decisao.assert_called_once_with(
        documento_id="DOC-1",
        decisao="corrigido",
        auditor_nome="Dra. Ana Silva",
        justificativa="Correção clínica revisada.",
        dados_corrigidos=esperado,
    )
    service.nosql_repo.gravar_evento.assert_called_once_with(
        documento_id="DOC-1",
        tipo_evento="DECISAO_MEDICA_CORRIGIDO",
        autor="Dra. Ana Silva",
        payload=esperado,
        justificativa="Correção clínica revisada.",
    )
