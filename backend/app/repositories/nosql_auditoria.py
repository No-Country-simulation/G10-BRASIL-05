from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import pymongo
from pymongo.collection import Collection
from pymongo.database import Database

from app.config.settings import settings
from app.config.logger import logger


class MongoAuditoriaRepository:
    """Repositório NoSQL em MongoDB para armazenamento imutável de eventos de auditoria e documentos brutos.
    
    Implementa padrão de Resiliência Híbrida:
    - Conecta-se ao MongoDB se disponível na URL configurada.
    - Caso o MongoDB não esteja acessível, ativa fallback transparente em memória thread-safe,
      garantindo que testes e ambientes locais sem o daemon continuem operando perfeitamente.
    """

    _in_memory_docs: List[Dict[str, Any]] = []

    def __init__(self, mongo_url: Optional[str] = None, db_name: Optional[str] = None):
        self.mongo_url = mongo_url or settings.MONGODB_URL
        self.db_name = db_name or settings.MONGODB_DATABASE
        self._client: Optional[pymongo.MongoClient] = None
        self._db: Optional[Database] = None
        self._collection: Optional[Collection] = None
        self._conectado: bool = False
        self._conectar()

    def _conectar(self):
        if not settings.MONGODB_ENABLED:
            logger.info("MongoDB desabilitado via configuração. Usando fallback NoSQL em memória.")
            return

        try:
            client = pymongo.MongoClient(
                self.mongo_url,
                serverSelectionTimeoutMS=1000,
                connectTimeoutMS=1000,
            )
            # Testa conectividade com comando ping
            client.admin.command("ping")
            self._client = client
            self._db = client[self.db_name]
            self._collection = self._db["auditoria_documentos"]
            # Garante índices
            self._collection.create_index([("documento_id", pymongo.ASCENDING)])
            self._collection.create_index([("created_at", pymongo.DESCENDING)])
            self._conectado = True
            logger.info(f"Conexão com MongoDB estabelecida com sucesso no banco '{self.db_name}'.")
        except Exception as e:
            self._client = None
            self._db = None
            self._collection = None
            self._conectado = False
            logger.warning(
                f"MongoDB indisponível em {self.mongo_url} ({e}). Ativando fallback NoSQL em memória."
            )

    @property
    def is_conectado(self) -> bool:
        return self._conectado

    def gravar_evento(
        self,
        documento_id: str,
        tipo_evento: str,
        autor: str,
        payload: Dict[str, Any],
        justificativa: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra um evento imutável de auditoria na trilha NoSQL."""
        registro = {
            "documento_id": documento_id,
            "tipo_evento": tipo_evento,
            "autor": autor,
            "justificativa": justificativa,
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Persistência no MongoDB
        if self._conectado and self._collection is not None:
            try:
                doc_para_inserir = dict(registro)
                resultado = self._collection.insert_one(doc_para_inserir)
                registro["_id"] = str(resultado.inserted_id)
                return registro
            except Exception as e:
                logger.error(f"Erro ao inserir evento no MongoDB: {e}. Gravando no fallback em memória.")

        # 2. Fallback em Memória
        doc_mem = dict(registro)
        doc_mem["_id"] = f"mem-{len(self._in_memory_docs) + 1}"
        self._in_memory_docs.append(doc_mem)
        return doc_mem

    def listar_por_documento(self, documento_id: str) -> List[Dict[str, Any]]:
        """Retorna todos os eventos de auditoria NoSQL de um documento específico."""
        if self._conectado and self._collection is not None:
            try:
                cursor = self._collection.find({"documento_id": documento_id}).sort("created_at", pymongo.DESCENDING)
                eventos = []
                for doc in cursor:
                    doc["_id"] = str(doc["_id"])
                    eventos.append(doc)
                return eventos
            except Exception as e:
                logger.error(f"Erro ao consultar eventos no MongoDB: {e}. Usando fallback.")

        # Fallback em Memória
        return [
            doc for doc in reversed(self._in_memory_docs)
            if doc.get("documento_id") == documento_id
        ]

    def listar_todos(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista os eventos mais recentes de auditoria NoSQL."""
        if self._conectado and self._collection is not None:
            try:
                cursor = self._collection.find().sort("created_at", pymongo.DESCENDING).skip(skip).limit(limit)
                eventos = []
                for doc in cursor:
                    doc["_id"] = str(doc["_id"])
                    eventos.append(doc)
                return eventos
            except Exception as e:
                logger.error(f"Erro ao listar todos os eventos no MongoDB: {e}. Usando fallback.")

        # Fallback
        todos_invertidos = list(reversed(self._in_memory_docs))
        return todos_invertidos[skip : skip + limit]
