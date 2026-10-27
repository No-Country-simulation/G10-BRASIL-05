import json
import time
from typing import Optional, Dict, Any, List
import redis

from app.config.settings import settings
from app.config.logger import logger


class RedisAuditService:
    """Serviço de gerenciamento de locks distribuídos e pub/sub de auditoria via Redis.
    
    Implementa padrão de Resiliência Híbrida:
    - Se o Redis estiver ativo, utiliza operações atômicas distribuídas (SET NX EX, PUBLISH).
    - Se o daemon Redis estiver offline (ex: ambiente de teste sem container),
      faz fallback automático para dicionário em memória thread-safe.
    """

    _in_memory_locks: Dict[str, Dict[str, Any]] = {}
    _in_memory_events: List[Dict[str, Any]] = []

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None
        self._conectado: bool = False
        self._conectar()

    def _conectar(self):
        if not settings.REDIS_ENABLED:
            logger.info("Redis desabilitado via configuração. Usando fallback em memória.")
            return

        try:
            client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
            )
            # Testa conectividade com ping rápido
            client.ping()
            self._client = client
            self._conectado = True
            logger.info(f"Conexão com Redis estabelecida com sucesso em {self.redis_url}.")
        except Exception as e:
            self._client = None
            self._conectado = False
            logger.warning(
                f"Redis indisponível em {self.redis_url} ({e}). Ativando fallback resiliente em memória."
            )

    @property
    def is_conectado(self) -> bool:
        return self._conectado

    def adquirir_lock(
        self,
        documento_id: str,
        auditor_nome: str,
        ttl_segundos: int = 300,
    ) -> bool:
        """Adquire lock exclusivo para revisão médica de um documento clínico."""
        chave = f"lock:auditoria:{documento_id}"

        # 1. Modo Redis Distribuído
        if self._conectado and self._client:
            try:
                # Tenta criar lock atômico
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

                # Se já existe, verifica se é do mesmo médico (reentrância)
                dono_atual = self._client.get(chave)
                if dono_atual == auditor_nome:
                    self._client.expire(chave, ttl_segundos)
                    return True
                return False
            except Exception as e:
                logger.error(f"Erro ao interagir com Redis em adquirir_lock: {e}. Usando fallback.")

        # 2. Modo Fallback em Memória
        agora = time.time()
        lock_atual = self._in_memory_locks.get(chave)

        # Se expirou, limpa
        if lock_atual and lock_atual["expira_em"] <= agora:
            lock_atual = None
            self._in_memory_locks.pop(chave, None)

        if lock_atual is None:
            self._in_memory_locks[chave] = {
                "auditor": auditor_nome,
                "expira_em": agora + ttl_segundos,
            }
            self.publicar_evento(
                "mediflow:auditoria:eventos",
                {
                    "tipo": "LOCK_ADQUIRIDO",
                    "documento_id": documento_id,
                    "auditor": auditor_nome,
                    "ttl": ttl_segundos,
                    "timestamp": agora,
                },
            )
            return True

        if lock_atual["auditor"] == auditor_nome:
            lock_atual["expira_em"] = agora + ttl_segundos
            return True

        return False

    def liberar_lock(self, documento_id: str, auditor_nome: str) -> bool:
        """Libera o lock exclusivo se o solicitante for o detentor atual do lock."""
        chave = f"lock:auditoria:{documento_id}"

        # 1. Modo Redis
        if self._conectado and self._client:
            try:
                dono_atual = self._client.get(chave)
                if dono_atual == auditor_nome:
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
                return False
            except Exception as e:
                logger.error(f"Erro ao interagir com Redis em liberar_lock: {e}. Usando fallback.")

        # 2. Modo Fallback
        lock_atual = self._in_memory_locks.get(chave)
        if not lock_atual:
            return True  # Já não existe lock

        if lock_atual["auditor"] == auditor_nome:
            self._in_memory_locks.pop(chave, None)
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

        return False

    def obter_status_lock(self, documento_id: str) -> Dict[str, Any]:
        """Informa se um documento está bloqueado e por qual médico."""
        chave = f"lock:auditoria:{documento_id}"

        if self._conectado and self._client:
            try:
                dono = self._client.get(chave)
                ttl = self._client.ttl(chave)
                if dono:
                    return {"bloqueado": True, "auditor": dono, "ttl_restante": max(0, ttl)}
                return {"bloqueado": False, "auditor": None, "ttl_restante": 0}
            except Exception:
                pass

        # Fallback
        agora = time.time()
        lock_atual = self._in_memory_locks.get(chave)
        if lock_atual and lock_atual["expira_em"] > agora:
            return {
                "bloqueado": True,
                "auditor": lock_atual["auditor"],
                "ttl_restante": int(lock_atual["expira_em"] - agora),
            }
        return {"bloqueado": False, "auditor": None, "ttl_restante": 0}

    def publicar_evento(self, canal: str, evento: Dict[str, Any]):
        """Publica evento no canal de telemetria / streaming."""
        payload_str = json.dumps(evento, default=str)
        if self._conectado and self._client:
            try:
                self._client.publish(canal, payload_str)
            except Exception as e:
                logger.debug(f"Falha ao publicar evento no Redis: {e}")

        # Mantém histórico recente em memória para consulta
        self._in_memory_events.append(evento)
        if len(self._in_memory_events) > 100:
            self._in_memory_events.pop(0)

    def listar_eventos_recentes(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._in_memory_events[-limit:]
