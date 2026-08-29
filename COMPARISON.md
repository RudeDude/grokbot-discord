# grokbot-discord vs discord-grok-bot-kit

A comparison of two independent Discord ↔ Grok Bot bridges that landed on the same day.

| | **grokbot-discord** (this repo) | **discord-grok-bot-kit** |
|---|---|---|
| Repo | [RudeDude/grokbot-discord](https://github.com/RudeDude/grokbot-discord) | [larry-fuqua/discord-grok-bot-kit](https://github.com/larry-fuqua/discord-grok-bot-kit) |
| Pitch | One Discord bot, many Grok Bots. Networked callback. Phone-anywhere control. | Drop-in Unix kit. One owner, one Grok Bot, same machine. |
| Created | 2026-08-29 16:27Z | 2026-08-29 17:21Z |
| Visibility | Private | Public |
| License | MIT | MIT |
| Relation | Not a fork | Not a fork |

They are not git-related. Same gap, same day, different products.

This write-up reflects **grokbot-discord** after it folded in several kit ideas (leading bot-name wake, instant **Got it.** ack, keep-alive scripts, MIT). The kit is described at commit [`0797998`](https://github.com/larry-fuqua/discord-grok-bot-kit/commit/0797998fbcd1e601c4bb42ae661edcc9ab911710).

---

## Same problem

Grok Bot has no Discord inbound plugin. Something has to:

1. Hold a Discord Gateway connection
2. Notice when the owner addresses a bot
3. POST a Grok Bot **webhook** so a routine wakes
4. Get a reply back into Discord

The webhook HTTP 200 means the Grok Bot *woke*, not that it finished. The real answer is always asynchronous.

```
Discord  --gateway-->  Python process  --POST webhook-->  Grok Bot
     ^                         |
     |                         |  (reply path differs)
     +------ channel post -----+
```

---

## The architectural split

This is the difference that drives everything else.

| | **grokbot-discord** | **discord-grok-bot-kit** |
|---|---|---|
| Reply path | Grok Bot HTTP POSTs `/reply` on the Python process | Grok Bot shells out to `bin/discord-send` |
| Coupling | Network (`reply_url` + `CALLBACK_SECRET`) | Shared filesystem (`last.json` + kit directory) |
| Bots | One Discord bot → many Grok Bots (`bots.yaml`) | One Discord bot → one Grok Bot |
| Where it can run | Same machine, or a Grok Bot elsewhere (Tailscale is enough) | Must share the machine with the Grok Bot |

**grokbot-discord** loop:

```
Discord → Python → webhook (payload includes reply_url + correlation_id)
                         ↘ Grok Bot POSTs /reply → Python posts Discord
```

**discord-grok-bot-kit** loop:

```
Discord → relay.py → webhook + write last.json + immediate "Got it."
                         ↘ Grok Bot reads last.json, runs bin/discord-send
```

The kit’s webhook prompt says the wake **may not include the POST body**, so `last.json` is the real source of truth. grokbot-discord assumes the JSON body arrives and tells the routine to parse it. That is a platform assumption. If Grok webhook routines drop the POST body, the kit’s side channel still works; this repo’s `reply_url` / `correlation_id` would not, unless the body actually lands.

---

## Feature matrix

| | grokbot-discord | discord-grok-bot-kit |
|---|---|---|
| Instant pickup ack (**Got it.**) | Yes | Yes |
| Multi-Grok routing | Name / alias / Discord role ID | Single `BOT_NAME` |
| Wake on leading bot name (no Discord `@`) | Yes (`loops ping` or `@loops ping`) | Yes (`BOT_NAME` / `@BOT_NAME` prefix) |
| Wake on Discord `@mention` of the bridge | Yes | Yes |
| Role wake | Mapped **role ID** in `bots.yaml` | Role **name** equals `BOT_NAME` |
| Allowlists | Guild + channel + author (fail-closed if empty) | One channel ID + one owner user ID |
| Other Discord bots | Allowlisted bot authors are accepted | Drops all `author.bot` |
| Dedup / in-flight cap | Yes (message-id LRU, 2/channel default) | No |
| Long replies | Split at 1900, prefer newlines | Truncate at 1900 |
| Threaded Discord reply | Yes (references the original message) | `discord-send` is a bare channel post |
| Dry-run | `DRY_RUN=true` | No |
| Health check | `GET /health` | Tail `relay.log` for `ready` |
| Process keep-alive | `watch.sh` + `ensure-up.sh` + scheduled Grok routine | Same pattern (`watch.sh` + `ensure-up.sh` + scheduled routine) |
| Tests / CI | pytest + ruff on PRs | None |
| Packaging | Python 3.12 package (`pyproject.toml`, src layout) | Script + `requirements.txt` + venv |
| Default Python deps | `discord.py>=2.4`, `aiohttp`, `pyyaml` | `discord.py==2.7.1` only |

---

## Wake syntax

**grokbot-discord** (allowlisted channel). You do not need both a Discord `@` and the bot name:

- `loops ping` or `@loops ping` — first token is a name or alias from `bots.yaml`
- `@bridge loops ping` — Discord mention of this bot, then the Grok Bot name
- mention a Discord role mapped in `bots.yaml`
- `@bridge ping` — uses `DEFAULT_BOT` / `default:` in yaml if set

Unknown names do not fire a webhook. The channel gets `unknown bot. configured: …`.

**discord-grok-bot-kit** (configured channel, owner only):

- `@mention` of the Discord bot user
- a role whose **name** equals `BOT_NAME` (case-insensitive)
- text starting with `BOT_NAME` or `@BOT_NAME`

There is only one target, so “unknown bot” does not exist.

---

## Code shape

**grokbot-discord** is a Python 3.12 package (`python -m grokbot_discord`):

| Path | Role |
|---|---|
| `src/grokbot_discord/bot.py` | Gateway, instant ack, pending correlation IDs |
| `src/grokbot_discord/filters.py` | Allowlists, dedupe, in-flight |
| `src/grokbot_discord/routing.py` | Name / alias / role |
| `src/grokbot_discord/webhook.py` | aiohttp POST, 8s timeout, `Authorization` + `X-Automation-Key` |
| `src/grokbot_discord/callback.py` | Bearer-auth `/reply` |
| `src/grokbot_discord/split.py` | Discord chunking |
| `prompts/webhook-routine.md` | Paste into each Grok Bot webhook routine |
| `prompts/keep-alive-routine.md` | In-repo copy of the **discord bridge watchdog** prompt |
| `watch.sh` / `ensure-up.sh` | Crash loop and start-if-missing |
| `tests/` | Routing, allowlists, webhook, callback auth, split |

**discord-grok-bot-kit** is a handful of scripts:

| Path | Role |
|---|---|
| `relay.py` | ~120-line `discord.Client`, stdlib `urllib` |
| `bin/discord-send` | stdlib POST to Discord REST |
| `watch.sh` / `ensure-up.sh` | Crash loop and start-if-missing |
| `examples/webhook-routine.md` | Grok Bot webhook prompt (read `last.json`, run `discord-send`) |
| `examples/keep-alive-routine.md` | Scheduled check after restarts |

Both load dotenv-style files the same way (skip comments, strip quotes). Secrets stay out of git in both.

---

## What each is better at

**grokbot-discord** if you want:

- several Grok Bots behind one Discord identity
- Grok Bots that are not on the same box as the listener
- fail-closed allowlists, tests, CI, dry-run
- replies correlated back to the original Discord message
- long answers split across Discord’s size limit

**discord-grok-bot-kit** if you want:

- copy the folder, fill `config.env`, `./ensure-up.sh`
- a Grok Bot that can send Discord messages without reaching an HTTP callback
- a workaround if Grok webhook routines drop the POST body (`last.json`)
- outbound send as a standalone CLI (`bin/discord-send`) from anywhere via `DISCORD_RELAY_DIR`

---

## What grokbot-discord took from the kit

After the first comparison, this repo absorbed the kit pieces that fit a multi-bot networked bridge:

- Leading bot-name wake, so a Discord `@mention` is not required when the first token is a configured name
- Instant **Got it.** ack, with the webhook prompt told not to send a second pickup ack
- `watch.sh` / `ensure-up.sh` and an in-repo keep-alive prompt (`prompts/keep-alive-routine.md`), documented against the live Grok Bot routine named **discord bridge watchdog**
- MIT license

Not folded in, on purpose:

- `last.json` / `bin/discord-send` (this repo’s reply path is HTTP `/reply`, not a shared disk)
- Single-owner / single-channel / single-bot config (this repo keeps allowlists and `bots.yaml`)
- Dropping every `author.bot` (this repo accepts allowlisted bot authors)

---

## Sources

- This repo: [RudeDude/grokbot-discord](https://github.com/RudeDude/grokbot-discord)
- The kit: [larry-fuqua/discord-grok-bot-kit](https://github.com/larry-fuqua/discord-grok-bot-kit) at [`0797998`](https://github.com/larry-fuqua/discord-grok-bot-kit/commit/0797998fbcd1e601c4bb42ae661edcc9ab911710) (2026-08-29)
