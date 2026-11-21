"""Publicação e leitura do estado recente dos eventos SSE da triagem."""

import json
from datetime import datetime, timezone

from redis import Redis

from app.config.logger import logger
from app.config.settings import settings
from app.services.triagem_queue import TTL_PROPRIETARIO_SEGUNDOS


def _chave_canal(usuario_id: int) -> str:
    return f"triagem:usuario:{usuario_id}:eventos"


def _chave_documentos(usuario_id: int) -> str:
    return f"triagem:usuario:{usuario_id}:eventos:documentos"


def _chave_estado(usuario_id: int, documento_id: str) -> str:
    return f"triagem:usuario:{usuario_id}:evento:{documento_id}"


def publicar_evento_triagem(usuario_id: int, evento: str, dados: dict) -> None:
    """Publica uma mudança e conserva o estado mais recente para reconexões SSE."""
    redis = Redis.from_url(settings.REDIS_URL)
    try:
        evento_id = redis.incr(f"{_chave_canal(usuario_id)}:sequencia")
        payload = {
            "id": str(evento_id),
            "evento": evento,
            "dados": {
                **dados,
                "atualizado_em": datetime.now(timezone.utc).isoformat(),
            },
        }
        documento_id = payload["dados"].get("documento_id")
        if documento_id:
            redis.setex(
                _chave_estado(usuario_id, documento_id),
                TTL_PROPRIETARIO_SEGUNDOS,
                json.dumps(payload, ensure_ascii=False),
            )
            redis.sadd(_chave_documentos(usuario_id), documento_id)
            redis.expire(_chave_documentos(usuario_id), TTL_PROPRIETARIO_SEGUNDOS)
        redis.publish(_chave_canal(usuario_id), json.dumps(payload, ensure_ascii=False))
    except Exception:
        logger.exception("Não foi possível publicar evento SSE da triagem para usuário %s", usuario_id)
    finally:
        redis.close()


def obter_eventos_estado_atual(usuario_id: int) -> list[dict]:
    """Retorna snapshots recentes para a conexão SSE recuperar atualizações perdidas."""
    redis = Redis.from_url(settings.REDIS_URL)
    try:
        documentos = redis.smembers(_chave_documentos(usuario_id))
        documentos_ids = [
            item.decode() if isinstance(item, bytes) else str(item)
            for item in documentos
        ]
        chaves = [
            _chave_estado(usuario_id, documento_id)
            for documento_id in documentos_ids
        ]
        if not chaves:
            return []
        estados = redis.mget(chaves)
        resultados = []
        expirados = []
        for documento_id, estado in zip(documentos_ids, estados):
            if not estado:
                expirados.append(documento_id)
                continue
            try:
                dados = estado.decode() if isinstance(estado, bytes) else estado
                resultados.append(json.loads(dados))
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning("Snapshot SSE da triagem inválido para usuário %s", usuario_id)
        if expirados:
            redis.srem(_chave_documentos(usuario_id), *expirados)
        return resultados
    finally:
        redis.close()
