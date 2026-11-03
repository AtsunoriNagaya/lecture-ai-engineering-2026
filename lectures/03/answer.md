# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：「lecNN-start タグとは？」に対し、第1回の `app.ask` は講座の資料を参照できないため「ノートブック内のコード区切りの目印」と推測で長く答えた（実際の意味とは違う）。エージェントは `search_glossary` で用語集を引き、「各回の演習開始時点のコードに付けた Git タグ（例: lec03-start）」と正しく短く答え、最後に「関連する回：第1回」を付けた。
- `--trace` で見えたツール呼び出し（ツール名と引数）：
  - 「lecNN-start タグとは？」→ `search_glossary({'query': 'lecNN-start タグ'})`
  - 「LoRAとQLoRAの違いは？」→ `search_glossary({'query': 'LoRA'})` と `search_glossary({'query': 'QLoRA'})` を1回の応答で並列に呼んだ。docstring の「query には用語を1つだけ入れる」に従い、2語を分けて検索している
  - 「第2回の内容から確認問題を1問出して」→ `make_quiz({'lecture': 2})`
- 1つの質問での LLM 呼び出し回数（`requests`）：どの質問も `requests=2`（ツールを呼ぶ判断で1回、ツールの結果を見て回答を作るので1回）。LoRA/QLoRA は `tool_calls=2` でも、2つの呼び出しが1回の応答にまとまっているので `requests=2` のままだった。
- 追加したツールと、docstring に書いた説明：`make_quiz(lecture: int)`。用語集から指定した回の用語を1つランダムに選び、「『用語』の意味は？」という問題と答え（定義）を JSON で返す。docstring には「『第2回の確認問題を出して』『復習のクイズがほしい』のように、理解度を確かめる問題を求められたときに使う」「answer はすぐに見せず、利用者が考えてから示す」と書いた。実行すると、モデルは答えを伏せて「考えてみてください」と問題だけを出した。

## 宿題

- 取り組んだレベル：実装、発展（a）

### 実装：承認付きの `save_learning_log`

- やったこと：
  - `app/tools.py` に `save_learning_log(title, content)` を追加。`learning_log/日時.md` に Markdown で保存する（`learning_log/` は .gitignore 済み）。保存先は定数 `LOG_DIR` にして、テストで一時フォルダに差し替えられるようにした
  - `app/agent.py` で `requires_approval=True` を付けて登録し、`output_type=[str, DeferredToolRequests]` にした
  - CLI（`main()`）は、結果が `DeferredToolRequests` なら呼び出そうとしているツール名と引数を表示して `[y/N]` で確認し、y なら `True`、それ以外なら `ToolDenied(...)` を `DeferredToolResults` に入れ、`message_history` と一緒に渡して続きを実行する。承認が続けて来ても対応できるよう `while` で回している
  - テスト（TestModel 使用、APIキー不要）を追加：承認前はファイルが作られず `DeferredToolRequests` が返る／承認するとファイルが1つ作られる／拒否すると作られない。`make_quiz` と `save_learning_log` 単体のテストも追加。`uv run pytest -q` → 17 passed
  - 既存の `test_base_tools_are_registered_and_called` は「全ツールを呼ぶと呼び出し数と結果数が一致する」ことを確かめていたが、承認待ちのツールは結果がまだ無いため 3 == 4 で失敗した。このテストでは承認付きツールを呼ばせないようにし、承認の流れは新しいテストで確かめる形にした
- 結果：
  - 最初の docstring には「保存は取り消しにくいため、実行前に利用者の承認を求める」と書いていた。すると「LoRAについて今日学んだ要点を学習記録として保存して」に対し、モデルは `save_learning_log` を呼ばずに文章で「保存してもよろしいですか？」と聞き返して終わった（trace は `search_glossary` だけ）。承認の仕組みに届かなかった
  - docstring を「保存してよいかの確認はシステムが利用者に行うので、文章で確認を求めずにこのツールを呼ぶ」に変えると、ツールが呼ばれて承認プロンプトが出た
    ```
    [approval] save_learning_log を実行しようとしています。
      content: # LoRAの学習要点 ...
      title: LoRAの学習要点
    実行してよいですか？ [y/N]: y
    → 20261103-194405-209132.md に保存しました。
    ```
  - N と答えたときは、ツールの結果として「利用者が実行を断りました。保存はしていません。」がモデルに返り、モデルは「今回は保存がキャンセルされました」と答えた。ファイルは作られなかった
  - 再開後の `result.usage` には再開後の分しか入っておらず `requests=1` と表示された。`run_sync(..., usage=result.usage)` で前の分を引き継ぐと `requests=3`（`search_glossary` を呼ぶ、`save_learning_log` を呼んで承認待ちになる、承認後に回答する）と合算されるようになった
- 気づき・疑問：
  - docstring はモデルへの指示なので、「承認を求める」と書くとモデル自身が確認しようとしてしまう。人による確認はコード側（`requires_approval`）の役割で、docstring には「モデルが何をすべきか」だけを書くほうがよいと分かった
  - 承認前に引数（保存する本文）を利用者に見せられるので、内容を確かめてから保存できる。`ToolApproved(override_args=...)` を使えば、利用者が本文を直してから保存することもできそう

### 発展（a）：Google ADK で作り直す

- やったこと：`adk_agent/glossary_agent/agent.py` と `__init__.py` を作成。`app/agent.py` の `INSTRUCTIONS` と、`app/tools.py` の `search_glossary`・`get_lecture_summary`・`make_quiz` をそのまま `Agent(model=..., name=..., instruction=..., tools=[...])` に渡した。モデルは演習と同じく `app/config.py` の `MODEL`（gemini-3.5-flash-lite）を使った。`app/` は変えていない。google-adk は 2.13.0
  ```bash
  PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent "LoRAとQLoRAの違いは？"
  ```
- 結果：
  - 書き方の違い：Pydantic AI は `Agent(instructions=...)` を作ってから `agent.tool_plain(関数)` で1つずつ登録する。ADK は `tools=[関数, ...]` にリストで渡し、変数名も `root_agent` と決まっている。どちらも関数の docstring と型ヒントからツールの説明を作るので、ツールのコードは共通で使えた。モデルは Pydantic AI では実行時に `run_sync(model=...)` で渡したが、ADK では `Agent` を作るときに文字列で渡す
  - 実行の違い：Pydantic AI は自分で書いた CLI（`app.agent`）から `run_sync` を呼ぶ。ADK は `adk run` がフォルダを読み込み、セッション管理や対話ループまで用意してくれる。一方で、`--trace` のようなツール呼び出しの表示は標準の画面には出ないため、`--log_level debug` のログから確認した
  - 同じ質問への回答（ツール呼び出しはログから確認）

    | 質問 | Pydantic AI | ADK |
    |---|---|---|
    | lecNN-start タグとは？ | `search_glossary('lecNN-start タグ')`。Git タグと正しく回答、関連する回：第1回 | ほぼ同じ文面の回答、関連する回：第1回 |
    | LoRAとQLoRAの違いは？ | `search_glossary('LoRA')`、`('QLoRA')` を並列 | 同じく `LoRA`・`QLoRA` を並列で呼んだ。回答の構成（箇条書き2つ＋関係する回：第2回）もほぼ同じ |
    | 第2回の確認問題を1問 | `make_quiz({'lecture': 2})` →「エポック」 | `make_quiz({'lecture': 2})` →「PEFT」（ランダムなので用語は毎回変わる） |

  - 同じモデル・同じ指示・同じツールなら、フレームワークを変えても呼ぶツールと引数、回答はほとんど変わらなかった
- 気づき・疑問：
  - エージェントの振る舞いを決めているのは主に「モデル＋指示＋ツールの説明」で、フレームワークはそれをモデルに渡してループを回す部分だと実感した。ツールを普通の Python 関数で書いておけば、フレームワークを乗り換えても使い回せる
  - 初回の `adk run` で利用データ送信（テレメトリ）を有効にするか聞かれた。`adk telemetry status` で未設定（既定で OFF）のままだと確認した
  - 疑問：ADK で承認付きツール（`save_learning_log`）を作るとき、Pydantic AI の `requires_approval` にあたる仕組みをどう使うか。今回は範囲外なので試していない。なお INSTRUCTIONS をそのまま使ったため、ADK 版の指示文には渡していない save_learning_log の名前が残っている。保存を頼まれたときにどう振る舞うかは未確認
