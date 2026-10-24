"""第1回: 素のLLMに1回だけ質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする
    uv run python -m app.ask --chat     # 会話履歴を保ったまま続けて質問する（第1回 宿題）

ツールも会話履歴も持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse

from google import genai
from google.genai import errors, types

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def print_usage(response) -> None:
    """入力トークン数と出力トークン数を表示する（第1回 演習）。"""
    usage = response.usage_metadata
    if usage:
        print(f"[tokens] 入力 {usage.prompt_token_count} / 出力 {usage.candidates_token_count}")


def ask(question: str) -> str:
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(model=MODEL, contents=question)
    print_usage(response)
    return response.text


def chat_turn(client, history: list[types.Content], question: str) -> str:
    """これまでの履歴に質問を足して送る。成功したときだけ、質問と回答を履歴に残す。"""
    user = types.Content(role="user", parts=[types.Part(text=question)])
    response = client.models.generate_content(model=MODEL, contents=[*history, user])
    print_usage(response)
    history += [user, types.Content(role="model", parts=[types.Part(text=response.text)])]
    return response.text


def chat() -> None:
    """会話履歴を保ったまま、続けて質問する（第1回 宿題：実装）。"""
    client = genai.Client(api_key=get_api_key())
    history: list[types.Content] = []
    print("続けて質問できます。空行か exit で終了します。")
    while True:
        try:
            question = input("\n[質問] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question in ("", "exit"):
            break
        try:
            print(chat_turn(client, history, question))
        except errors.APIError as e:
            # 失敗したターンは履歴に残さず、次の質問を受け付ける
            print(api_error_message(e.code, e.message))


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--chat", action="store_true", help="会話履歴を保ったまま続けて質問する")
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    if args.chat:
        chat()
        return
    print(f"[質問] {args.question}\n")
    try:
        print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
