from grokbot_discord.models import IncomingMessage


def make_msg(**overrides) -> IncomingMessage:
    base = dict(
        message_id="m1",
        channel_id="c1",
        guild_id="g1",
        author_id="u1",
        author_name="don",
        content="<@bridge> loops ping",
        mention_user_ids=frozenset({"bridge"}),
        mention_role_ids=frozenset(),
    )
    base.update(overrides)
    return IncomingMessage(**base)
