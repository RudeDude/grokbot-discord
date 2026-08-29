# Discord bridge watchdog (keep-alive)

A scheduled Grok Bot routine named **discord bridge watchdog** is already saved on the live bot. This file is the in-repo copy of that routine so it can be recreated if it drifts or is deleted. The live prompt was not previously kept in git.

Adapted from the [discord-grok-bot-kit](https://github.com/larry-fuqua/discord-grok-bot-kit) keep-alive.

`watch.sh` restarts `python -m grokbot_discord` if the process dies. After a computer reboot, nothing starts `watch.sh` unless a keep-alive runs `ensure-up.sh`.

## Grok Bot scheduled routine

Create (or keep) a **scheduled** routine named **discord bridge watchdog** that runs `./ensure-up.sh` in this repo directory.

Stay quiet if the listener is already up. Only message the owner if it could not be started.

Discord pings can arrive any day, including weekends. A several-times-daily cadence works: 08:15, 12:15, 16:15, and 20:15 local, all seven days.

### Example routine prompt

```
Check that the Discord bridge listener is running on this computer.

If watch.sh or the grokbot_discord process is not running in the grokbot-discord repo directory, run ./ensure-up.sh from that directory (.venv python, not system python). Confirm bridge.log recently shows "online as".

Stay quiet if the listener is already up. Only message the owner if the listener could not be started.
```

## Optional cron

```
@reboot /path/to/grokbot-discord/ensure-up.sh
15 8,12,16,20 * * * /path/to/grokbot-discord/ensure-up.sh
```
