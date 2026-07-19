"""README 갱신 필터 골든셋.

should_update_readme(diff, changed_files, commit_messages, client) 가 "이 변경이
README 갱신을 필요로 하는가"를 얼마나 정확히 판정하는지 채점하기 위한 라벨 데이터.

needs_readme = 사용자에게 보이는 변경(기능/API/실행법/설정/의존성/폴더구조/권한)이
있어 README를 갱신해야 하는가. 내부 리팩터/테스트/오타/툴링 설정 = False.

diff 는 여러 줄이라 JSON 대신 Python 문자열 리터럴로 둔다. 각 케이스는 실제
git diff 형태(+/- 라인 포함)를 따르되, 판정 로직을 명확히 자극하도록 최소화했다.
"""

CASES = [
    # ---- README 갱신 필요 (needs_readme=True) ----
    {
        "name": "새 CLI 옵션 추가",
        "changed_files": ["src/github_ai_agent/cli.py"],
        "commit_messages": ["feat: add --json output flag"],
        "needs_readme": True,
        "diff": """diff --git a/src/github_ai_agent/cli.py b/src/github_ai_agent/cli.py
@@ -20,6 +20,7 @@ def async_main():
     parser.add_argument("--repo", help="GitHub repo.")
+    parser.add_argument("--json", action="store_true", help="Print JSON output.")
""",
    },
    {
        "name": "새 HTTP 엔드포인트 추가",
        "changed_files": ["src/github_ai_agent/app.py"],
        "commit_messages": ["feat: add /health endpoint"],
        "needs_readme": True,
        "diff": """diff --git a/src/github_ai_agent/app.py b/src/github_ai_agent/app.py
@@ -40,3 +40,7 @@ def index():
+@app.get("/health")
+def health():
+    return {"ok": True}
""",
    },
    {
        "name": "새 의존성 추가",
        "changed_files": ["pyproject.toml"],
        "commit_messages": ["chore: add httpx dependency"],
        "needs_readme": True,
        "diff": """diff --git a/pyproject.toml b/pyproject.toml
@@ -10,6 +10,7 @@ dependencies = [
   "openai>=1.90.0",
+  "httpx>=0.27.0",
   "python-dotenv>=1.0.1",
""",
    },
    {
        "name": "공개 함수 시그니처 변경",
        "changed_files": ["src/github_ai_agent/notion_client.py"],
        "commit_messages": ["refactor: pass token to create_task"],
        "needs_readme": True,
        "diff": """diff --git a/src/github_ai_agent/notion_client.py b/src/github_ai_agent/notion_client.py
@@ -30,3 +30,3 @@ class NotionToolClient:
-def create_task(title):
+def create_task(title, token):
     return _post(title)
""",
    },
    {
        "name": "새 통합 클라이언트(공개 클래스) 추가",
        "changed_files": ["src/github_ai_agent/slack_client.py"],
        "commit_messages": ["feat: add slack integration"],
        "needs_readme": True,
        "diff": """diff --git a/src/github_ai_agent/slack_client.py b/src/github_ai_agent/slack_client.py
@@ -0,0 +1,5 @@
+class SlackToolClient:
+    def send(self, message):
+        return _post(message)
""",
    },

    # ---- README 갱신 불필요 (needs_readme=False) ----
    {
        "name": "문서만 수정(오타)",
        "changed_files": ["README.md"],
        "commit_messages": ["docs: fix typo"],
        "needs_readme": False,
        "diff": """diff --git a/README.md b/README.md
@@ -5,1 +5,1 @@
-실행 방법은 아래와 같습나다.
+실행 방법은 아래와 같습니다.
""",
    },
    {
        "name": "테스트만 추가",
        "changed_files": ["tests/test_agent.py"],
        "commit_messages": ["test: add intent case"],
        "needs_readme": False,
        "diff": """diff --git a/tests/test_agent.py b/tests/test_agent.py
@@ -0,0 +1,3 @@
+def test_intent():
+    assert classify("안녕").intent == "conversation"
""",
    },
    {
        "name": "툴링 설정 변경(.gitignore)",
        "changed_files": [".gitignore"],
        "commit_messages": ["chore: ignore db files"],
        "needs_readme": False,
        "diff": """diff --git a/.gitignore b/.gitignore
@@ -8,0 +9,1 @@
+*.db
""",
    },
    {
        "name": "내부 private 함수 이름 변경",
        "changed_files": ["src/github_ai_agent/agent.py"],
        "commit_messages": ["refactor: rename internal helper"],
        "needs_readme": False,
        "diff": """diff --git a/src/github_ai_agent/agent.py b/src/github_ai_agent/agent.py
@@ -50,3 +50,3 @@ class Agent:
-def _build_ctx(x):
+def _build_context(x):
     return x
""",
    },
    {
        "name": "주석만 수정",
        "changed_files": ["src/github_ai_agent/web.py"],
        "commit_messages": ["style: clarify comment"],
        "needs_readme": False,
        "diff": """diff --git a/src/github_ai_agent/web.py b/src/github_ai_agent/web.py
@@ -100,1 +100,1 @@
-    # old note
+    # clearer note explaining the routing flow
""",
    },
    {
        "name": "내부 private 함수 추가",
        "changed_files": ["src/github_ai_agent/harness.py"],
        "commit_messages": ["refactor: extract helper"],
        "needs_readme": False,
        "diff": """diff --git a/src/github_ai_agent/harness.py b/src/github_ai_agent/harness.py
@@ -60,0 +61,2 @@ class AgentHarness:
+def _normalize(text):
+    return text.strip().lower()
""",
    },
    {
        "name": "내부 포매팅 유틸(공개명이나 사용자 무관)",
        "changed_files": ["src/github_ai_agent/webapp/task_planning.py"],
        "commit_messages": ["refactor: tidy chat answer"],
        "needs_readme": False,
        "diff": """diff --git a/src/github_ai_agent/webapp/task_planning.py b/src/github_ai_agent/webapp/task_planning.py
@@ -100,0 +101,2 @@
+def clean_answer_for_chat(text):
+    return text.strip()
""",
    },
    {
        "name": "코드 포매팅만 변경",
        "changed_files": ["src/github_ai_agent/cli.py"],
        "commit_messages": ["style: apply formatter"],
        "needs_readme": False,
        "diff": """diff --git a/src/github_ai_agent/cli.py b/src/github_ai_agent/cli.py
@@ -12,1 +12,1 @@
-x=1
+x = 1
""",
    },
]
