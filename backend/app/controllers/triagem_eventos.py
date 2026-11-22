"""Stream SSE autenticado para atualizações da fila de triagem."""

import asyncio
import json

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis as AsyncRedis

from app.config.settings import settings
from app.models.triagem import UsuarioSistemaModel
from app.services.autenticacao import exigir_papeis_cookie
from app.services.triagem_eventos import obter_eventos_estado_atual
from app.services.triagem_queue import obter_lote_triagem


def _formatar_evento(evento: dict) -> str:
    dados = json.dumps(evento.get("dados", {}), ensure_ascii=False, separators=(",", ":"))
    return f"id: {evento.get('id', '')}\nevent: {evento.get('evento', 'status_update')}\ndata: {dados}\n\n"


async def stream_eventos_triagem(
    request: Request,
    lote_id: str | None = Query(default=None),
    token: str | None = Query(default=None),
    usuario: UsuarioSistemaModel = Depends(
        exigir_papeis_cookie("ADMIN_GERAL", "DIRETOR", "MEDICO", "ENFERMEIRO")
    ),
):
    """Entrega snapshots e mudanças em tempo real só para o usuário autenticado."""
    documentos_lote: set[str] | None = None
    usuario_eventos_id = usuario.id
    if lote_id:
        lote = obter_lote_triagem(lote_id)
        if lote is None or (
            lote.get("usuario_id") != usuario.id and usuario.papel != "ADMIN_GERAL"
        ):
            raise HTTPException(status_code=404, detail="Lote de triagem não encontrado.")
        usuario_eventos_id = lote["usuario_id"]
        documentos_lote = {
            item.get("documento_id")
            for item in lote.get("trabalhos", [])
            if item.get("documento_id")
        }

    canal = f"triagem:usuario:{usuario_eventos_id}:eventos"

    async def gerar_eventos():
        redis = AsyncRedis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis.pubsub()
        try:
            await pubsub.subscribe(canal)
            snapshots = await asyncio.to_thread(obter_eventos_estado_atual, usuario_eventos_id)
            for evento in snapshots:
                documento_id = (evento.get("dados") or {}).get("documento_id")
                if documentos_lote is None or documento_id in documentos_lote:
                    yield _formatar_evento(evento)

            while not await request.is_disconnected():
                mensagem = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=15.0,
                )
                if mensagem and mensagem.get("data"):
                    try:
                        evento = json.loads(mensagem["data"])
                    except (TypeError, json.JSONDecodeError):
                        continue
                    documento_id = (evento.get("dados") or {}).get("documento_id")
                    if documentos_lote is None or documento_id in documentos_lote:
                        yield _formatar_evento(evento)
                else:
                    yield ": keep-alive\n\n"
        finally:
            await pubsub.unsubscribe(canal)
            await pubsub.aclose()
            await redis.aclose()

    return StreamingResponse(
        gerar_eventos(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
