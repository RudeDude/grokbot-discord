from grokbot_discord.models import WAKE_FIELDS, WakePayload
from grokbot_discord.webhook import WEBHOOK_TIMEOUT_S, DryRunResult, ping, webhook_request


def test_headers_timeout_no_retry():
    req = webhook_request("https://example.test/hook", "the-key", {"bot": "loops"})
    assert req["headers"]["Authorization"] == "Bearer the-key"
    assert req["headers"]["X-Automation-Key"] == "the-key"
    assert req["headers"]["Content-Type"] == "application/json"
    assert req["timeout"] == 8.0
    assert WEBHOOK_TIMEOUT_S == 8.0
    assert "retry" not in req


def test_payload_fields():
    payload = WakePayload(
        bot="loops",
        text="ping",
        author_id="u1",
        author_name="don",
        channel_id="c1",
        guild_id="g1",
        message_id="m1",
        reply_url="http://127.0.0.1:8787/reply",
        correlation_id="abc",
    )
    body = payload.as_dict()
    assert tuple(body.keys()) == WAKE_FIELDS
    assert set(body) == set(WAKE_FIELDS)


async def test_dry_run_does_not_need_session():
    payload = WakePayload(
        bot="loops",
        text="ping",
        author_id="u1",
        author_name="don",
        channel_id="c1",
        guild_id="g1",
        message_id="m1",
        reply_url="http://127.0.0.1:8787/reply",
        correlation_id="abc",
    )
    result = await ping(None, "https://example.test/hook", "key", payload, dry_run=True)
    assert isinstance(result, DryRunResult)
    assert result.payload["bot"] == "loops"
    assert result.payload["text"] == "ping"
