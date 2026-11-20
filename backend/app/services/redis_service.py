import json
import time
from typing import Any

import redis

from app.config.settings import settings
from app.errors import DependencyUnavailableError


class RedisAuditService:
    """Locks, idempotência e eventos de auditoria persistidos no Redis."""

    _eventos_recentes = "mediflow:auditoria:recentes"

    def __init__(self, redis_url: str | None = None):
        url = settings.REDIS_URL if redis_url is None else redis_url
        try:
            self._client = redis.Redis.from_url(
                url,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
            )
            self._client.ping()
        except Exception as erro:
            raise DependencyUnavailableError(
                "Redis indisponível; operações de auditoria não podem continuar."
            ) from erro

    @property
    def is_conectado(self) -> bool:
        return True

    def adquirir_lock(self, documento_id: str, auditor_nome: str, ttl_segundos: int = 300) -> bool:
        chave = f"lock:auditoria:{documento_id}"
        adquiriu = self._client.set(chave, auditor_nome, nx=True, ex=ttl_segundos)
        if adquiriu:
            self.publicar_evento(
                "mediflow:auditoria:eventos",
                {
                    "tipo": "LOCK_ADQUIRIDO",
                    "documento_id": documento_id,
                    "auditor": auditor_nome,
                    "ttl": ttl_segundos,
                    "timestamp": time.time(),
                },
            )
            return True
        dono_atual = self._client.get(chave)
        if dono_atual == auditor_nome:
            self._client.expire(chave, ttl_segundos)
            return True
        return False

    def liberar_lock(self, documento_id: str, auditor_nome: str) -> bool:
        chave = f"lock:auditoria:{documento_id}"
        dono_atual = self._client.get(chave)
        if dono_atual is None:
            return True
        if dono_atual != auditor_nome:
            return False
        self._client.delete(chave)
        self.publicar_evento(
            "mediflow:auditoria:eventos",
            {
                "tipo": "LOCK_LIBERADO",
                "documento_id": documento_id,
                "auditor": auditor_nome,
                "timestamp": time.time(),
            },
        )
        return True

    def obter_status_lock(self, documento_id: str) -> dict[str, Any]:
        chave = f"lock:auditoria:{documento_id}"
        dono = self._client.get(chave)
        ttl = self._client.ttl(chave) if dono else 0
        return {
            "bloqueado": bool(dono),
            "auditor": dono,
            "ttl_restante": max(0, ttl),
        }

    def publicar_evento(self, canal: str, evento: dict[str, Any]) -> None:
        payload = json.dumps(evento, ensure_ascii=False)
        pipeline = self._client.pipeline(transaction=True)
        pipeline.publish(canal, payload)
        pipeline.rpush(self._eventos_recentes, payload)
        pipeline.ltrim(self._eventos_recentes, -100, -1)
        pipeline.execute()

    def listar_eventos_recentes(self, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 0:
            raise ValueError("O limite de eventos não pode ser negativo.")
        eventos = self._client.lrange(self._eventos_recentes, -limit if limit else 0, -1) if limit else []
        return [json.loads(evento) for evento in eventos]

    def registrar_idempotencia(self, chave: str, ttl_segundos: int = 86400) -> bool:
        chave_completa = f"idempotencia:{chave}"
        return bool(self._client.set(chave_completa, "1", nx=True, ex=ttl_segundos))

    def salvar_sessao_whatsapp(self, numero: str, dados: dict[str, Any], ttl_segundos: int = 86400) -> None:
        """Salva contexto e memória de atendimento do WhatsApp no Redis."""
        chave = f"whatsapp:sessao:{numero}"
        payload = json.dumps(dados, ensure_ascii=False)
        self._client.set(chave, payload, ex=ttl_segundos)

    def obter_sessao_whatsapp(self, numero: str) -> dict[str, Any] | None:
        """Recupera contexto e memória de atendimento do WhatsApp."""
        chave = f"whatsapp:sessao:{numero}"
        valor = self._client.get(chave)
        if not valor:
            return None
        try:
            return json.loads(valor)
        except Exception:
            return None
