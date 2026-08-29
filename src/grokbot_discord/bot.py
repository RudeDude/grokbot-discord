from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from typing import Any

import aiohttp
import discord

from grokbot_discord.callback import build_app, start_site
from grokbot_discord.config import ConfigError, Settings, load_settings
from grokbot_discord.filters import Dedupe, InFlight, should_drop
from grokbot_discord.models import IncomingMessage, WakePayload
from grokbot_discord.routing import addressed_by_name, mapped_role_ids, route
from grokbot_discord.split import split_message
from grokbot_discord.webhook import DryRunResult, ping

log = logging.getLogger("grokbot_discord")
ACK_TEXT = "Got it."


def _incoming(message: discord.Message) -> IncomingMessage:
    guild_id = str(message.guild.id) if message.guild else ""
    return IncomingMessage(
        message_id=str(message.id),
        channel_id=str(message.channel.id),
        guild_id=guild_id,
        author_id=str(message.author.id),
        author_name=str(getattr(message.author, "display_name", message.author.name)),
        content=message.content or "",
        mention_user_ids=frozenset(str(u.id) for u in message.mentions),
        mention_role_ids=frozenset(str(r.id) for r in message.role_mentions),
    )


class BridgeClient(discord.Client):
    def __init__(self, settings: Settings, **kwargs: Any) -> None:
        intents = kwargs.pop("intents", None) or discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        super().__init__(intents=intents, **kwargs)
        self.settings = settings
        self.dedupe = Dedupe()
        self.in_flight = InFlight(settings.in_flight_per_channel)
        self.pending: dict[str, tuple[str, str]] = {}
        self.http_session: aiohttp.ClientSession | None = None
        self._runner = None
        self.dry_run_log: list[dict[str, str]] = []

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession()
        app = build_app(self.settings.callback_secret, self._on_callback)
        self._runner = await start_site(
            app, self.settings.callback_bind, self.settings.callback_port
        )

    async def close(self) -> None:
        if self.http_session is not None:
            await self.http_session.close()
        if self._runner is not None:
            await self._runner.cleanup()
        await super().close()

    async def on_ready(self) -> None:
        log.info("online as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if self.user is None:
            return
        msg = _incoming(message)
        self_id = str(self.user.id)
        named = addressed_by_name(msg.content, self.settings.bots, self_user_id=self_id)
        reason = should_drop(
            msg,
            self_user_id=self_id,
            guilds=self.settings.guilds,
            channels=self.settings.channels,
            authors=self.settings.authors,
            require_mention=self.settings.require_mention,
            mapped_role_ids=mapped_role_ids(self.settings.bots),
            dedupe=self.dedupe,
            named=named,
        )
        if reason:
            return
        hit = route(
            msg,
            self.settings.bots,
            self_user_id=self_id,
            default_bot=self.settings.default_bot,
        )
        if hit is None:
            names = ", ".join(sorted(self.settings.bots))
            await message.channel.send(f"unknown bot. configured: {names}")
            return
        if not self.in_flight.acquire(msg.channel_id):
            return
        try:
            await message.reply(ACK_TEXT, mention_author=False)
        except Exception:
            log.exception("ack failed for message_id=%s", msg.message_id)
        correlation_id = uuid.uuid4().hex
        self.pending[correlation_id] = (msg.channel_id, msg.message_id)
        payload = WakePayload(
            bot=hit.bot.name,
            text=hit.text,
            author_id=msg.author_id,
            author_name=msg.author_name,
            channel_id=msg.channel_id,
            guild_id=msg.guild_id,
            message_id=msg.message_id,
            reply_url=f"{self.settings.callback_public_url}/reply",
            correlation_id=correlation_id,
        )
        asyncio.create_task(self._wake(hit.bot.webhook_url, hit.bot.webhook_key, payload))

    async def _wake(self, url: str, key: str, payload: WakePayload) -> None:
        keep_pending = False
        try:
            if self.http_session is None:
                return
            result = await ping(
                self.http_session,
                url,
                key,
                payload,
                dry_run=self.settings.dry_run,
            )
            if isinstance(result, DryRunResult):
                self.dry_run_log.append(result.payload)
                log.info("DRY_RUN would POST webhook for bot=%s", payload.bot)
                return
            if result != 200:
                log.warning("webhook wake returned %s for bot=%s", result, payload.bot)
                return
            keep_pending = True
        except TimeoutError:
            log.warning("webhook wake timed out for bot=%s", payload.bot)
        except aiohttp.ClientError:
            log.exception("webhook wake failed for bot=%s", payload.bot)
        finally:
            if keep_pending:
                return
            self.in_flight.release(payload.channel_id)
            self.pending.pop(payload.correlation_id, None)

    async def _on_callback(
        self, correlation_id: str, channel_id: str, message_id: str, text: str
    ) -> None:
        pending = self.pending.pop(correlation_id, None)
        ref_channel, ref_message = pending if pending else (channel_id, message_id)
        try:
            channel = self.get_channel(int(ref_channel))
            if channel is None:
                channel = await self.fetch_channel(int(ref_channel))
            chunks = split_message(text)
            reference = None
            if ref_message:
                try:
                    reference = discord.MessageReference(
                        message_id=int(ref_message),
                        channel_id=int(ref_channel),
                        fail_if_not_exists=False,
                    )
                except ValueError:
                    reference = None
            for i, chunk in enumerate(chunks):
                kwargs: dict[str, Any] = {}
                if i == 0 and reference is not None:
                    kwargs["reference"] = reference
                await channel.send(chunk, **kwargs)
        finally:
            self.in_flight.release(ref_channel)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        settings = load_settings()
    except ConfigError as exc:
        log.error("%s", exc)
        sys.exit(2)
    client = BridgeClient(settings)
    client.run(settings.discord_token)
