from tests.conftest import make_msg

from grokbot_discord.routing import route


def test_alias_first_token(bots):
    msg = make_msg(content="<@bridge> loops ping", mention_user_ids=frozenset({"bridge"}))
    hit = route(msg, bots, self_user_id="bridge", default_bot="loops")
    assert hit is not None
    assert hit.bot.name == "loops"
    assert hit.text == "ping"


def test_role_mention(bots):
    msg = make_msg(
        content="<@&role-xo> status",
        mention_user_ids=frozenset(),
        mention_role_ids=frozenset({"role-xo"}),
    )
    hit = route(msg, bots, self_user_id="bridge", default_bot="loops")
    assert hit is not None
    assert hit.bot.name == "xo"
    assert "status" in hit.text


def test_multi_role_is_unknown(bots):
    msg = make_msg(
        content="hey",
        mention_user_ids=frozenset({"bridge"}),
        mention_role_ids=frozenset({"role-loops", "role-xo"}),
    )
    assert route(msg, bots, self_user_id="bridge", default_bot="loops") is None


def test_default_when_only_bot_mentioned(bots):
    msg = make_msg(content="<@bridge> what is in flight?", mention_user_ids=frozenset({"bridge"}))
    hit = route(msg, bots, self_user_id="bridge", default_bot="loops")
    assert hit is not None
    assert hit.bot.name == "loops"
    assert "what is in flight?" in hit.text


def test_unknown_name(bots):
    msg = make_msg(content="<@bridge> no-such ping", mention_user_ids=frozenset({"bridge"}))
    hit = route(msg, bots, self_user_id="bridge", default_bot="")
    assert hit is None
