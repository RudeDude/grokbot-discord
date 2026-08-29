# grokbot-discord

Python Discord gateway for talking to Grok Bots from a private server. One Discord bot, many Grok Bots. Built so you can chat from a phone anywhere Discord works.

Grok Bot has no Discord inbound plugin. A long-running process holds the Gateway, hears `@mentions`, POSTs a webhook ping to wake the target Grok Bot, then posts the reply when that bot calls back.

```
Discord  --gateway-->  Python process  --POST webhook-->  Grok Bot
     ^                         |
     |                         |  POST /reply
     +------ channel post -----+
```

The webhook returns 200 when the Grok Bot *wakes*, not when it finishes. Replies are async.

## 1. Discord application

1. Open [Discord Developer Portal](https://discord.com/developers/applications) → New Application.
2. Bot → Add Bot. Enable **Message Content Intent**.
3. Reset Token and copy it. That is `DISCORD_BOT_TOKEN`. Never commit it.
4. OAuth2 → URL Generator. Scopes: `bot`. Permissions: View Channels, Send Messages, Read Message History.
5. Open the URL, invite the bot into a **private** server and the channel you will use.
6. Discord Settings → Advanced → Developer Mode. Right-click the server, channel, and your user → Copy ID. Those are the allowlists.

## 2. One webhook routine per Grok Bot

On each Grok Bot:

1. Create a routine with trigger type `webhook`.
2. Use [prompts/webhook-routine.md](prompts/webhook-routine.md) as the prompt.
3. Open the routine panel. Copy the webhook URL (`https://api2.cursor.sh/automations/webhook/<id>`).
4. Copy the sender key. Do not paste the key into chat or git.

## 3. Local config

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
cp bots.example.yaml bots.yaml
```

Fill `.env`:

- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ALLOWLIST`, `DISCORD_CHANNEL_ALLOWLIST`, `DISCORD_AUTHOR_ALLOWLIST` (comma-separated snowflakes)
- `CALLBACK_SECRET` (a long random string the Grok Bots use when they POST replies)
- `GROK_BOT_<NAME>_WEBHOOK_URL` and `GROK_BOT_<NAME>_WEBHOOK_KEY` for each bot in `bots.yaml`

Empty allowlists refuse to start. Empty bots list refuses to start. Missing webhook URL/key refuses to start unless `DRY_RUN=true`.

`bots.yaml` maps names, aliases, and optional Discord role IDs to those env vars. Keys stay in env.

## 4. Run

```bash
.venv/bin/pytest
.venv/bin/python -m grokbot_discord
```

Logs `online as YourBot#1234` when the Gateway is up. The process also listens on `CALLBACK_BIND:CALLBACK_PORT` (default `127.0.0.1:8787`) for `/health` and `/reply`.

Dry-run first, no Grok Bot keys required:

```bash
DRY_RUN=true .venv/bin/python -m grokbot_discord
```

Mentions are logged as would-POST. Nothing leaves the machine.

## 5. Talk to a bot

In the allowlisted channel:

- `@bridge loops ping` — first token after the Discord bot mention is the Grok Bot name
- mention a Discord role mapped in `bots.yaml`
- `@bridge ping` — uses `DEFAULT_BOT` / `default:` in yaml if set

An unknown name does not fire a webhook. The channel gets `unknown bot. configured: …`.

## 6. Where this runs

Grok Bots on the same Linux machine should use `CALLBACK_PUBLIC_URL=http://127.0.0.1:8787`. If a Grok Bot is elsewhere, bind `CALLBACK_BIND=0.0.0.0` and set `CALLBACK_PUBLIC_URL` to an address that bot can reach (Tailscale is enough). Do not put the sender key or `CALLBACK_SECRET` in the browser or in git.

## Routing and filters

A message is dropped when:

- the author is this Discord bot
- guild, channel, or author is not allowlisted (allowlisted *bots* are accepted; there is no blanket `author.bot` drop)
- `REQUIRE_MENTION=true` and neither this Discord bot nor a mapped role was mentioned
- `message_id` was already handled
- the channel already has `IN_FLIGHT_PER_CHANNEL` wakes waiting on a reply (default 2)

## Layout

- `src/grokbot_discord/` — Gateway, filters, routing, webhook client, reply callback
- `prompts/webhook-routine.md` — paste into each Grok Bot webhook routine
- `.github/workflows/ci.yml` — `ruff` + `pytest` on PRs
