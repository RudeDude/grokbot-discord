from tests.conftest import make_msg

from grokbot_discord.filters import ConfigError, Dedupe, InFlight, require_allowlists, should_drop


def test_empty_allowlists_fail_closed():
    for args in (
        (set(), {"c"}, {"u"}),
        ({"g"}, set(), {"u"}),
        ({"g"}, {"c"}, set()),
    ):
        try:
            require_allowlists(*args)
        except ConfigError:
            pass
        else:
            raise AssertionError("expected ConfigError")


def test_drops():
    dedupe = Dedupe()
    msg = make_msg()
    kwargs = dict(
        self_user_id="bridge",
        guilds={"g1"},
        channels={"c1"},
        authors={"u1"},
        require_mention=True,
        mapped_role_ids={"role-loops"},
        dedupe=dedupe,
    )
    assert should_drop(msg, **kwargs) is None
    assert should_drop(msg, **kwargs) == "duplicate"

    assert should_drop(make_msg(author_id="bridge", message_id="m2"), **kwargs) == "self"
    assert should_drop(make_msg(guild_id="nope", message_id="m3"), **kwargs) == "guild"
    assert should_drop(make_msg(channel_id="nope", message_id="m4"), **kwargs) == "channel"
    assert should_drop(make_msg(author_id="stranger", message_id="m5"), **kwargs) == "author"
    assert (
        should_drop(
            make_msg(
                message_id="m6",
                mention_user_ids=frozenset(),
                mention_role_ids=frozenset(),
            ),
            **kwargs,
        )
        == "mention"
    )


def test_allowlisted_bot_author_is_not_dropped():
    msg = make_msg(author_id="other-bot", message_id="m7")
    reason = should_drop(
        msg,
        self_user_id="bridge",
        guilds={"g1"},
        channels={"c1"},
        authors={"u1", "other-bot"},
        require_mention=True,
        mapped_role_ids=set(),
        dedupe=Dedupe(),
    )
    assert reason is None


def test_in_flight_overflow():
    inflight = InFlight(2)
    assert inflight.acquire("c1")
    assert inflight.acquire("c1")
    assert not inflight.acquire("c1")
    inflight.release("c1")
    assert inflight.acquire("c1")
