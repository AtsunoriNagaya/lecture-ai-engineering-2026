"""ask.py の会話履歴のテスト。

偽のクライアントを使い、実際のLLMを呼ばずに
「2ターン目のリクエストに1ターン目の質問と回答が含まれるか」を確かめる。
"""

from types import SimpleNamespace

from app.ask import chat_turn


class FakeModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, model, contents):
        self.calls.append(list(contents))
        return SimpleNamespace(text=f"回答{len(self.calls)}", usage_metadata=None)


def _texts(contents):
    return [(c.role, c.parts[0].text) for c in contents]


def test_second_turn_includes_first_turn():
    client = SimpleNamespace(models=FakeModels())
    history = []

    assert chat_turn(client, history, "私の名前は太郎です") == "回答1"
    assert chat_turn(client, history, "私の名前は？") == "回答2"

    assert _texts(client.models.calls[1]) == [
        ("user", "私の名前は太郎です"),
        ("model", "回答1"),
        ("user", "私の名前は？"),
    ]
    assert len(history) == 4
