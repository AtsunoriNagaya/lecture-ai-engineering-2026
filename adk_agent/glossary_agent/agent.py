"""第3回 宿題（発展a）: 演習と同じ指示とツールで、エージェントの組み立てだけを Google ADK で書き直す。

動かし方（リポジトリの直下で）:
    PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent

app/ のファイルは変えずに、INSTRUCTIONS とツール関数をそのまま読み込む。
ADK も Pydantic AI と同じく、関数の docstring と型ヒントからツールの説明を作る。
"""

from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS
from app.config import MODEL

root_agent = Agent(
    model=MODEL,  # 演習と同じモデル（既定は gemini-3.5-flash-lite。AIE_MODEL で切り替え）
    name="glossary_agent",
    instruction=INSTRUCTIONS,
    # 承認付きの save_learning_log は宿題の範囲外なので渡さない
    tools=[tools.search_glossary, tools.get_lecture_summary, tools.make_quiz],
)
