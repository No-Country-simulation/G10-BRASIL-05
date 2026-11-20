"""Fila Redis de trabalhos independentes de triagem."""

import json

from redis import Redis
from rq import Queue

from app.config.settings import settings


NOME_FILA_TRIAGEM = "triagem"
MAX_TRABALHOS_ATIVOS_POR_USUARIO = 10
TTL_PROPRIETARIO_SEGUNDOS = 24 * 60 * 60


def obter_redis_fila() -> Redis:
    return Redis.from_url(settings.REDIS_URL)


def obter_fila_triagem() -> Queue:
    return Queue(NOME_FILA_TRIAGEM, connection=obter_redis_fila())


def chave_trabalhos_usuario(usuario_id: int) -> str:
    return f"triagem:usuario:{usuario_id}:trabalhos"


def chave_proprietario_documento(documento_id: str) -> str:
    return f"triagem:documento:{documento_id}:proprietario"


def chave_lote_triagem(lote_id: str) -> str:
    return f"triagem:lote:{lote_id}"


def registrar_lote_triagem(lote_id: str, usuario_id: int, trabalhos: list[dict]) -> None:
    redis = obter_redis_fila()
    redis.set(
        chave_lote_triagem(lote_id),
        json.dumps({"usuario_id": usuario_id, "trabalhos": trabalhos}, ensure_ascii=False),
        ex=TTL_PROPRIETARIO_SEGUNDOS,
    )


def obter_lote_triagem(lote_id: str) -> dict | None:
    dados = obter_redis_fila().get(chave_lote_triagem(lote_id))
    if dados is None:
        return None
    if isinstance(dados, bytes):
        dados = dados.decode("utf-8")
    return json.loads(dados)


def reservar_trabalho(usuario_id: int, documento_id: str) -> int:
    """Reserva atomicamente uma vaga de fila para limitar lotes por usuário."""
    redis = obter_redis_fila()
    return int(
        redis.eval(
            """
            if redis.call('SISMEMBER', KEYS[1], ARGV[1]) == 1
              or redis.call('EXISTS', KEYS[2]) == 1 then return -1 end
            local ativos = redis.call('SCARD', KEYS[1])
            if ativos >= tonumber(ARGV[2]) then return 0 end
            redis.call('SADD', KEYS[1], ARGV[1])
            redis.call('EXPIRE', KEYS[1], ARGV[3])
            redis.call('SET', KEYS[2], ARGV[4], 'EX', ARGV[3])
            return 1
            """,
            2,
            chave_trabalhos_usuario(usuario_id),
            chave_proprietario_documento(documento_id),
            documento_id,
            MAX_TRABALHOS_ATIVOS_POR_USUARIO,
            TTL_PROPRIETARIO_SEGUNDOS,
            usuario_id,
        )
    )


def liberar_reserva(usuario_id: int, documento_id: str, remover_proprietario: bool = True) -> None:
    redis = obter_redis_fila()
    redis.srem(chave_trabalhos_usuario(usuario_id), documento_id)
    if remover_proprietario:
        redis.delete(chave_proprietario_documento(documento_id))


def enfileirar_documento(
    *,
    documento_id: str,
    caminho_arquivo: str,
    caminho_objeto_fonte: str,
    nome_arquivo: str,
    extensao: str,
    canal_origem: str,
    usuario_id: int,
):
    fila = obter_fila_triagem()
    return fila.enqueue(
        "app.services.triagem_worker.processar_documento_enfileirado",
        documento_id=documento_id,
        caminho_arquivo=caminho_arquivo,
        caminho_objeto_fonte=caminho_objeto_fonte,
        nome_arquivo=nome_arquivo,
        extensao=extensao,
        canal_origem=canal_origem,
        usuario_id=usuario_id,
        job_id=documento_id,
        job_timeout=1800,
        result_ttl=0,
        failure_ttl=TTL_PROPRIETARIO_SEGUNDOS,
    )


def enfileirar_texto(
    *,
    documento_id: str,
    documento_texto: str,
    tipo_arquivo: str,
    canal_origem: str,
    usuario_id: int,
):
    """Enfileira texto colado pelo mesmo worker dos arquivos enviados."""
    fila = obter_fila_triagem()
    return fila.enqueue(
        "app.services.triagem_worker.processar_documento_enfileirado",
        documento_id=documento_id,
        caminho_arquivo=None,
        caminho_objeto_fonte=None,
        nome_arquivo="Texto colado",
        extensao=tipo_arquivo,
        canal_origem=canal_origem,
        usuario_id=usuario_id,
        texto_documento=documento_texto,
        job_id=documento_id,
        job_timeout=1800,
        result_ttl=0,
        failure_ttl=TTL_PROPRIETARIO_SEGUNDOS,
    )
