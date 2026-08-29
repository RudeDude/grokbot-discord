from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from aiohttp import web
from aiohttp.client_exceptions import ContentTypeError

from grokbot_discord.split import split_message

log = logging.getLogger("grokbot_discord")

ReplyHandler = Callable[[str, str, str, str], Awaitable[None]]


def _bearer(header: str) -> str:
    if not header:
        return ""
    kind, _, rest = header.partition(" ")
    if kind.lower() != "bearer":
        return ""
    return rest.strip()


def build_app(secret: str, on_reply: ReplyHandler) -> web.Application:
    app = web.Application()

    async def health(_: web.Request) -> web.Response:
        return web.Response(text="ok")

    async def reply(request: web.Request) -> web.Response:
        token = _bearer(request.headers.get("Authorization", ""))
        if not secret or token != secret:
            return web.Response(status=401, text="unauthorized")
        try:
            body = await request.json()
        except (ContentTypeError, ValueError):
            return web.Response(status=400, text="invalid json")
        if not isinstance(body, dict):
            return web.Response(status=400, text="invalid json")
        correlation_id = str(body.get("correlation_id") or "")
        channel_id = str(body.get("channel_id") or "")
        message_id = str(body.get("message_id") or "")
        text = str(body.get("text") or "")
        if not correlation_id or not channel_id:
            return web.Response(status=400, text="missing fields")
        chunks = split_message(text)
        if not chunks:
            return web.Response(status=204)
        await on_reply(correlation_id, channel_id, message_id, text)
        return web.json_response({"ok": True, "chunks": len(chunks)})

    app.router.add_get("/health", health)
    app.router.add_post("/reply", reply)
    return app


async def start_site(app: web.Application, bind: str, port: int) -> web.AppRunner:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, bind, port)
    await site.start()
    log.info("callback listening on %s:%s", bind, port)
    return runner
