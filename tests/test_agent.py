"""エージェントの配線テスト。

TestModel は実際のLLMを呼ばない偽モデルで、登録されたツールを全部呼んでから
ダミーの回答を返す。APIキーも利用枠も使わずに、
「ツールが登録され、呼ばれ、結果がモデルに戻るか」を確かめられる。
"""

from pydantic_ai import DeferredToolRequests, DeferredToolResults, ToolDenied
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import agent

BASE_TOOLS = {"search_glossary", "get_lecture_summary"}


def _parts(result, kind):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, kind)]


def test_base_tools_are_registered_and_called():
    # 承認付きのツール（save_learning_log）は呼ぶと承認待ちで止まるため、ここでは呼ばせない
    model = TestModel(call_tools=sorted(BASE_TOOLS | {"make_quiz"}))
    with agent.override(model=model):
        result = agent.run_sync("LoRAとは？")

    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert BASE_TOOLS <= offered  # 演習でツールを足しても壊れないよう「含む」で判定

    called = {p.tool_name for p in _parts(result, ToolCallPart)}
    assert BASE_TOOLS <= called
    assert len(_parts(result, ToolReturnPart)) == len(_parts(result, ToolCallPart))
    assert result.output


def test_glossary_result_reaches_the_model():
    model = TestModel(call_tools=["search_glossary"])
    with agent.override(model=model):
        result = agent.run_sync("RAGとは？")
    returns = _parts(result, ToolReturnPart)
    assert returns and returns[0].tool_name == "search_glossary"


# --- 第3回 宿題（実装）: 承認付きの save_learning_log ---


def _request_save(monkeypatch, tmp_path):
    """save_learning_log だけを呼ばせ、承認待ちで止まった結果を返す。保存先は一時フォルダ。"""
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path / "learning_log")
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        result = agent.run_sync("今日学んだことを保存して")
    return model, result


def test_save_learning_log_waits_for_approval(monkeypatch, tmp_path):
    _, result = _request_save(monkeypatch, tmp_path)
    assert isinstance(result.output, DeferredToolRequests)
    assert [c.tool_name for c in result.output.approvals] == ["save_learning_log"]
    assert not (tmp_path / "learning_log").exists()  # 承認前なので何も保存されていない


def test_save_learning_log_saves_after_approval(monkeypatch, tmp_path):
    model, result = _request_save(monkeypatch, tmp_path)
    approvals = {c.tool_call_id: True for c in result.output.approvals}
    with agent.override(model=model):
        result = agent.run_sync(
            message_history=result.all_messages(),
            deferred_tool_results=DeferredToolResults(approvals=approvals),
        )
    assert isinstance(result.output, str)
    saved = list((tmp_path / "learning_log").glob("*.md"))
    assert len(saved) == 1
    returns = [p for p in _parts(result, ToolReturnPart) if p.tool_name == "save_learning_log"]
    assert "保存しました" in returns[0].content


def test_save_learning_log_denied_does_not_save(monkeypatch, tmp_path):
    model, result = _request_save(monkeypatch, tmp_path)
    approvals = {c.tool_call_id: ToolDenied("保存しない") for c in result.output.approvals}
    with agent.override(model=model):
        result = agent.run_sync(
            message_history=result.all_messages(),
            deferred_tool_results=DeferredToolResults(approvals=approvals),
        )
    assert isinstance(result.output, str)
    assert not (tmp_path / "learning_log").exists()
