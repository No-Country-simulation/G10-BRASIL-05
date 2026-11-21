from fastapi import APIRouter, Depends, Response, status
from app.services.health_service import verificar_prontidao_sistema

from app.config.settings import settings
from app.controllers.auditoria import (
    baixar_fonte_original,
    bloquear_documento_auditoria,
    consultar_trilha_nosql,
    listar_eventos_redis,
    listar_fila_auditoria,
    registrar_decisao_auditoria,
    desbloquear_documento_auditoria,
    verificar_status_lock,
)
from app.controllers.auth import (
    alterar_senha,
    atualizar_usuario,
    desativar_usuario,
    definir_cookie_sessao,
    encerrar_sessao_cookie,
    listar_usuarios,
    login,
    obter_sessao,
    provisionar_usuario,
)
from app.controllers.ecossistema import (
    listar_hospitais,
    listar_medicos,
    listar_pacientes,
    obter_historico_paciente,
    obter_paciente,
)
from app.controllers.evolution import (
    auto_configurar_webhook,
    conectar_whatsapp_qrcode,
    consultar_status_instancia,
    desconectar_whatsapp,
    enviar_mensagem_teste,
)
from app.controllers.evolution_webhook import receber_webhook_evolution, verificar_status_webhook
from app.controllers.historico import listar_documentos
from app.controllers.triagem import processar_triagem
from app.controllers.triagem_eventos import stream_eventos_triagem
from app.controllers.triagem_upload import inspecionar_extracao_documento, processar_upload_triagem
from app.controllers.triagem_jobs import (
    consultar_trabalho_triagem,
    enfileirar_texto_triagem,
    enfileirar_upload_triagem,
)
from app.schemas.auth import LoginResponse, UsuarioAutenticado
from app.schemas.ecossistema import (
    HospitalResponse,
    MedicoResponse,
    PacienteHistoricoResponse,
    PacienteResponse,
)
from app.schemas.triagem import RespostaTriagem
from app.services.autenticacao import exigir_papeis


api_router = APIRouter()


def _register_route(
    path: str,
    endpoint,
    *,
    methods: list[str],
    **kwargs,
) -> None:
    """Registra cada endpoint no caminho versionado e no caminho legado."""
    paths = [path]
    if settings.API_V1_PREFIX:
        paths.insert(0, f"{settings.API_V1_PREFIX.rstrip('/')}{path}")

    for route_path in paths:
        api_router.add_api_route(route_path, endpoint, methods=methods, **kwargs)


_triagem_access = [Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO", "ENFERMEIRO"))]
_auditoria_access = [Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO"))]

# Triagem clínica
_register_route(
    "/triagem", processar_triagem, methods=["POST"], tags=["Triagem Clínica"],
    response_model=RespostaTriagem, status_code=status.HTTP_200_OK, dependencies=_triagem_access,
)
_register_route(
    "/triagem/inspecionar", inspecionar_extracao_documento, methods=["POST"],
    tags=["Triagem Clínica"], dependencies=_triagem_access,
)
_register_route(
    "/triagem/upload", processar_upload_triagem, methods=["POST"], tags=["Triagem Clínica"],
    response_model=RespostaTriagem, status_code=status.HTTP_201_CREATED,
    dependencies=_triagem_access,
)
_register_route(
    "/triagem/upload/enfileirar", enfileirar_upload_triagem, methods=["POST"],
    tags=["Triagem Clínica"], status_code=status.HTTP_202_ACCEPTED,
    dependencies=_triagem_access,
)
_register_route(
    "/triagem/texto/enfileirar", enfileirar_texto_triagem, methods=["POST"],
    tags=["Triagem Clínica"], status_code=status.HTTP_202_ACCEPTED,
    dependencies=_triagem_access,
)
_register_route(
    "/triagem/trabalhos/{documento_id}", consultar_trabalho_triagem, methods=["GET"],
    tags=["Triagem Clínica"], status_code=status.HTTP_200_OK,
    dependencies=_triagem_access,
)
_register_route(
    "/triagem/eventos/stream", stream_eventos_triagem, methods=["GET"],
    tags=["Triagem Clínica"], status_code=status.HTTP_200_OK,
)

# Histórico e auditoria clínica
_register_route(
    "/triagem/documentos", listar_documentos, methods=["GET"], tags=["Histórico de Triagem"],
    status_code=status.HTTP_200_OK, dependencies=_triagem_access,
)
_register_route(
    "/triagem/auditoria", listar_fila_auditoria, methods=["GET"], tags=["Auditoria Clínica"],
    status_code=status.HTTP_200_OK, dependencies=_auditoria_access,
)
_register_route(
    "/triagem/auditoria/{documento_id}/fonte", baixar_fonte_original,
    methods=["GET"], tags=["Auditoria Clínica"], status_code=status.HTTP_200_OK,
    dependencies=_auditoria_access,
)
_register_route(
    "/triagem/auditoria/{documento_id}/decisao", registrar_decisao_auditoria,
    methods=["POST"], tags=["Auditoria Clínica"], status_code=status.HTTP_200_OK,
    dependencies=_auditoria_access,
)
_register_route(
    "/triagem/auditoria/{documento_id}/bloquear", bloquear_documento_auditoria,
    methods=["POST"], tags=["Auditoria Clínica"], status_code=status.HTTP_200_OK,
    dependencies=_auditoria_access,
)
_register_route(
    "/triagem/auditoria/{documento_id}/desbloquear", desbloquear_documento_auditoria,
    methods=["POST"], tags=["Auditoria Clínica"], status_code=status.HTTP_200_OK,
    dependencies=_auditoria_access,
)
_register_route(
    "/triagem/auditoria/{documento_id}/status-lock", verificar_status_lock,
    methods=["GET"], tags=["Auditoria Clínica"], status_code=status.HTTP_200_OK,
    dependencies=_auditoria_access,
)
_register_route(
    "/triagem/auditoria/{documento_id}/trilha-nosql", consultar_trilha_nosql,
    methods=["GET"], tags=["Auditoria Clínica"], status_code=status.HTTP_200_OK,
    dependencies=_auditoria_access,
)
_register_route(
    "/triagem/auditoria/eventos-redis", listar_eventos_redis,
    methods=["GET"], tags=["Auditoria Clínica"], status_code=status.HTTP_200_OK,
    dependencies=_auditoria_access,
)

# Ecossistema clínico
_ecossistema_access = [Depends(exigir_papeis("ADMIN_GERAL", "DIRETOR", "MEDICO", "ENFERMEIRO"))]
_register_route(
    "/pacientes", listar_pacientes, methods=["GET"],
    tags=["Ecossistema Clínico (Hospitais, Médicos e Pacientes)"],
    response_model=list[PacienteResponse], status_code=status.HTTP_200_OK,
    dependencies=_ecossistema_access,
)
_register_route(
    "/pacientes/{paciente_id}", obter_paciente, methods=["GET"],
    tags=["Ecossistema Clínico (Hospitais, Médicos e Pacientes)"],
    response_model=PacienteResponse, status_code=status.HTTP_200_OK,
    dependencies=_ecossistema_access,
)
_register_route(
    "/pacientes/{paciente_id}/historico", obter_historico_paciente, methods=["GET"],
    tags=["Ecossistema Clínico (Hospitais, Médicos e Pacientes)"],
    response_model=PacienteHistoricoResponse, status_code=status.HTTP_200_OK,
    dependencies=_ecossistema_access,
)
_register_route(
    "/medicos", listar_medicos, methods=["GET"],
    tags=["Ecossistema Clínico (Hospitais, Médicos e Pacientes)"],
    response_model=list[MedicoResponse], status_code=status.HTTP_200_OK,
    dependencies=_ecossistema_access,
)
_register_route(
    "/hospitais", listar_hospitais, methods=["GET"],
    tags=["Ecossistema Clínico (Hospitais, Médicos e Pacientes)"],
    response_model=list[HospitalResponse], status_code=status.HTTP_200_OK,
    dependencies=_ecossistema_access,
)

# Evolution API e webhook recebido
_evolution_tag = ["WhatsApp (Evolution API)"]
_register_route("/webhook/evolution/enviar-teste", enviar_mensagem_teste, methods=["POST"], tags=_evolution_tag, status_code=status.HTTP_200_OK)
_register_route("/webhook/evolution/status-instancia", consultar_status_instancia, methods=["GET"], tags=_evolution_tag, status_code=status.HTTP_200_OK)
_register_route("/webhook/evolution/conectar", conectar_whatsapp_qrcode, methods=["POST"], tags=_evolution_tag, status_code=status.HTTP_200_OK)
_register_route("/webhook/evolution/configurar-webhook", auto_configurar_webhook, methods=["POST"], tags=_evolution_tag, status_code=status.HTTP_200_OK)
_register_route("/webhook/evolution/desconectar", desconectar_whatsapp, methods=["POST"], tags=_evolution_tag, status_code=status.HTTP_200_OK)
_register_route("/webhook/evolution", verificar_status_webhook, methods=["GET"], tags=_evolution_tag, status_code=status.HTTP_200_OK)
_register_route("/webhook/evolution", receber_webhook_evolution, methods=["POST"], tags=_evolution_tag, status_code=status.HTTP_200_OK)
_register_route("/webhook/evolution/{evento_path}", receber_webhook_evolution, methods=["POST"], tags=_evolution_tag, status_code=status.HTTP_200_OK)

# Autenticação e usuários
_auth_tag = ["Autenticação e Usuários"]
_register_route("/auth/login", login, methods=["POST"], tags=_auth_tag, response_model=LoginResponse)
_register_route("/auth/me", obter_sessao, methods=["GET"], tags=_auth_tag, response_model=UsuarioAutenticado)
_register_route("/auth/session-cookie", definir_cookie_sessao, methods=["POST"], tags=_auth_tag)
_register_route("/auth/logout", encerrar_sessao_cookie, methods=["POST"], tags=_auth_tag)
_register_route("/auth/password", alterar_senha, methods=["PUT"], tags=_auth_tag)
_register_route("/auth/usuarios", listar_usuarios, methods=["GET"], tags=_auth_tag, response_model=list[UsuarioAutenticado])
_register_route(
    "/auth/usuarios", provisionar_usuario, methods=["POST"], tags=_auth_tag,
    response_model=UsuarioAutenticado, status_code=status.HTTP_201_CREATED,
)
_register_route(
    "/auth/usuarios/{usuario_id}", atualizar_usuario, methods=["PATCH"],
    tags=_auth_tag, response_model=UsuarioAutenticado,
)
_register_route(
    "/auth/usuarios/{usuario_id}", desativar_usuario, methods=["DELETE"],
    tags=_auth_tag, status_code=status.HTTP_204_NO_CONTENT,
)


@api_router.get("/", tags=["Root"])
def root():
    """Metadados básicos da API MediFlow."""
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "status": "online",
        "docs": "/docs",
    }


@api_router.get("/health", tags=["Health"])
def health_check(response: Response):
    """Endpoint de verificação de saúde e prontidão da aplicação."""
    resultado = verificar_prontidao_sistema()
    if resultado["status"] != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "healthy" if resultado["status"] == "ready" else "unhealthy",
        "environment": settings.APP_ENV,
        "database": resultado["dependencias"]["postgres"]["detalhe"],
        "dependencias": resultado["dependencias"],
    }


@api_router.get("/health/live", tags=["Health"])
def liveness_check():
    """Liveness probe: indica apenas se o processo HTTP está em execução."""
    return {"status": "alive", "app": settings.APP_NAME}


@api_router.get("/health/ready", tags=["Health"])
def readiness_check(response: Response):
    """Readiness probe: mede conexões reais aos bancos requeridos (PostgreSQL, Redis, Mongo)."""
    resultado = verificar_prontidao_sistema()
    if resultado["status"] != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return resultado
