from grokbot_discord.split import split_message


def test_empty():
    assert split_message("") == []
    assert split_message("   ") == []


def test_under_limit():
    assert split_message("hello") == ["hello"]


def test_prefers_newline():
    text = ("a" * 100 + "\n") + ("b" * 1800)
    parts = split_message(text, limit=1900)
    assert len(parts) == 2
    assert parts[0].endswith("a")
    assert parts[1].startswith("b")


def test_hard_cut_when_no_newline():
    text = "x" * 4000
    parts = split_message(text, limit=1900)
    assert [len(p) for p in parts] == [1900, 1900, 200]
    assert "".join(parts) == text
