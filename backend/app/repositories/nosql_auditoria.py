from datetime import datetime, timezone
from typing import Any

import pymongo
from pymongo.collection import Collection
from pymongo.database import Database

from app.config.settings import settings
from app.errors import DependencyUnavailableError


class ErroIntegridadeOutbox(RuntimeError):
    integridade_outbox = True


class MongoAuditoriaRepository:
    """Persiste eventos de auditoria exclusivamente no MongoDB."""

    def __init__(self, mongo_url: str | None = None, db_name: str | None = None):
        url = settings.MONGODB_URL if mongo_url is None else mongo_url
        nome_banco = settings.MONGODB_DATABASE if db_name is None else db_name
        try:
            self._client = pymongo.MongoClient(
                url,
                serverSelectionTimeoutMS=1000,
                connectTimeoutMS=1000,
            )
            self._client.admin.command("ping")
        except Exception as erro:
            raise DependencyUnavailableError(
                "MongoDB indisponível; operações de auditoria não podem continuar."
            ) from erro

        self._db: Database = self._client[nome_banco]
        self._collection: Collection = self._db["auditoria_documentos"]
        self._collection.create_index(
            [("evento_id", pymongo.ASCENDING)], unique=True,
            partialFilterExpression={"evento_id": {"$type": "string"}},
            name="uq_auditoria_evento_id",
        )
        self._collection.create_index(
            [("documento_id", pymongo.ASCENDING), ("sequencia", pymongo.ASCENDING)],
            unique=True,
            partialFilterExpression={"sequencia": {"$type": "number"}},
            name="uq_auditoria_documento_sequencia",
        )
        self._collection.create_index(
            [("documento_id", pymongo.ASCENDING), ("sequencia", pymongo.ASCENDING),
             ("created_at", pymongo.ASCENDING), ("_id", pymongo.ASCENDING)],
            name="ix_auditoria_timeline",
        )

    def fechar(self) -> None:
        self._client.close()

    def inserir_evento_idempotente(self, evento: dict[str, Any]) -> dict[str, Any]:
        envelope = evento["payload"]
        registro = {
            "evento_id": str(evento["evento_id"]),
            "documento_id": evento["documento_externo_id"],
            "sequencia": evento["sequencia"],
            "tipo_evento": evento["tipo_evento"],
            "autor": envelope.get("autor"),
            "justificativa": envelope.get("justificativa"),
            "payload": envelope.get("payload", {}),
            "payload_hash": evento["payload_hash"],
            "created_at": evento["ocorrido_em"],
        }
        try:
            resultado = self._collection.insert_one(registro)
            registro["_id"] = str(resultado.inserted_id)
            return registro
        except pymongo.errors.DuplicateKeyError as erro:
            existente = self._collection.find_one({"evento_id": registro["evento_id"]})
            if (
                existente
                and existente.get("documento_id") == registro["documento_id"]
                and existente.get("sequencia") == registro["sequencia"]
                and existente.get("tipo_evento") == registro["tipo_evento"]
                and existente.get("payload_hash") == registro["payload_hash"]
            ):
                existente["_id"] = str(existente["_id"])
                return existente
            conflito = self._collection.find_one({
                "documento_id": registro["documento_id"],
                "sequencia": registro["sequencia"],
            })
            if conflito:
                raise ErroIntegridadeOutbox(
                    "Conflito de integridade no stream: sequência já ocupada por evento diferente."
                ) from erro
            raise ErroIntegridadeOutbox("Conflito de integridade: evento_id já existe com conteúdo diferente.") from erro

    @property
    def is_conectado(self) -> bool:
        return True

    def gravar_evento(
        self,
        documento_id: str,
        tipo_evento: str,
        autor: str,
        payload: dict[str, Any],
        justificativa: str | None = None,
    ) -> dict[str, Any]:
        registro = {
            "documento_id": documento_id,
            "tipo_evento": tipo_evento,
            "autor": autor,
            "justificativa": justificativa,
            "payload": payload,
            "created_at": datetime.now(timezone.utc),
        }
        resultado = self._collection.insert_one(dict(registro))
        registro["_id"] = str(resultado.inserted_id)
        return registro

    def listar_por_documento(self, documento_id: str) -> list[dict[str, Any]]:
        cursor = self._collection.find({"documento_id": documento_id}).sort(
            [("sequencia", pymongo.ASCENDING), ("created_at", pymongo.ASCENDING), ("_id", pymongo.ASCENDING)]
        )
        eventos = []
        for documento in cursor:
            documento["_id"] = str(documento["_id"])
            if isinstance(documento.get("created_at"), datetime):
                documento["created_at"] = documento["created_at"].isoformat()
            eventos.append(documento)
        return eventos

    def listar_todos(self, skip: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        if skip < 0 or limit < 0:
            raise ValueError("Skip e limite não podem ser negativos.")
        cursor = self._collection.find().sort("created_at", pymongo.DESCENDING).skip(skip).limit(limit)
        eventos = []
        for documento in cursor:
            documento["_id"] = str(documento["_id"])
            if isinstance(documento.get("created_at"), datetime):
                documento["created_at"] = documento["created_at"].isoformat()
            eventos.append(documento)
        return eventos
