from __future__ import annotations

import re

from grokbot_discord.models import BotSpec, IncomingMessage, Route


def strip_user_mention(content: str, user_id: str) -> str:
    return re.sub(rf"<@!?{re.escape(user_id)}>", "", content)


def strip_role_mention(content: str, role_id: str) -> str:
    if not role_id:
        return content
    return content.replace(f"<@&{role_id}>", "")


def _alias_map(bots: dict[str, BotSpec]) -> dict[str, BotSpec]:
    out: dict[str, BotSpec] = {}
    for bot in bots.values():
        out[bot.name.casefold()] = bot
        for alias in bot.aliases:
            out[alias.casefold()] = bot
    return out


def mapped_role_ids(bots: dict[str, BotSpec]) -> set[str]:
    return {b.role_id for b in bots.values() if b.role_id}


def route(
    msg: IncomingMessage,
    bots: dict[str, BotSpec],
    *,
    self_user_id: str,
    default_bot: str,
) -> Route | None:
    if not bots:
        return None
    roles = [b for b in bots.values() if b.role_id and b.role_id in msg.mention_role_ids]
    if len(roles) > 1:
        return None
    if len(roles) == 1:
        bot = roles[0]
        text = strip_user_mention(msg.content, self_user_id)
        text = strip_role_mention(text, bot.role_id)
        return Route(bot=bot, text=text.strip())

    text = strip_user_mention(msg.content, self_user_id).strip()
    aliases = _alias_map(bots)
    if text:
        first, _, rest = text.partition(" ")
        hit = aliases.get(first.casefold())
        if hit is not None:
            return Route(bot=hit, text=rest.strip())

    if default_bot and self_user_id in msg.mention_user_ids:
        bot = bots.get(default_bot) or aliases.get(default_bot.casefold())
        if bot is not None:
            return Route(bot=bot, text=text)
    return None
