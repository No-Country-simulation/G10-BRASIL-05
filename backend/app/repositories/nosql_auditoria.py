from datetime import datetime, timezone
from typing import Any

import pymongo
from pymongo.collection import Collection
from pymongo.database import Database

from app.config.settings import settings
from app.errors import DependencyUnavailableError


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
        self._collection.create_index([("documento_id", pymongo.ASCENDING)])
        self._collection.create_index([("created_at", pymongo.DESCENDING)])

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
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        resultado = self._collection.insert_one(dict(registro))
        registro["_id"] = str(resultado.inserted_id)
        return registro

    def listar_por_documento(self, documento_id: str) -> list[dict[str, Any]]:
        cursor = self._collection.find({"documento_id": documento_id}).sort(
            "created_at", pymongo.DESCENDING
        )
        eventos = []
        for documento in cursor:
            documento["_id"] = str(documento["_id"])
            eventos.append(documento)
        return eventos

    def listar_todos(self, skip: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        if skip < 0 or limit < 0:
            raise ValueError("Skip e limite não podem ser negativos.")
        cursor = self._collection.find().sort("created_at", pymongo.DESCENDING).skip(skip).limit(limit)
        eventos = []
        for documento in cursor:
            documento["_id"] = str(documento["_id"])
            eventos.append(documento)
        return eventos
