"""의도 분류 정확도 평가.

harness.classify_intent 의 라우팅 결정(requires_project_context)을 골든셋과
비교해 정확도 / precision / recall / F1 / 혼동행렬을 계산한다. 양성(positive)은
"저장소 접근이 필요함(True)". 그래서:
  - False Positive = 접근이 불필요한데 접근으로 라우팅 (불필요한 GitHub MCP 호출)
  - False Negative = 접근이 필요한데 일반 답변으로 라우팅 (조회 놓침)

정의성 질문 예외(commit a7e1197)의 효과를 보이기 위해, 현재(after) 분류기와
그 직전(before, a7e1197~1) 분류기를 같은 골든셋으로 함께 채점해 비교한다.

실행: python eval/eval_intent.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = Path(__file__).resolve().parent / "intent_golden.json"
BEFORE_REV = "a7e1197~1"  # 정의성 예외가 들어가기 직전 커밋


def _load_current_classifier():
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from github_ai_agent.harness import AgentHarness

    return AgentHarness().classify_intent


def _load_classifier_from_git(rev: str):
    """git의 특정 리비전에 있던 harness.py 를 임시 모듈로 불러온다.
    harness.py 는 표준 라이브러리만 import 하므로 단독 로딩이 가능하다."""
    try:
        source = subprocess.run(
            ["git", "show", f"{rev}:src/github_ai_agent/harness.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(source)
        tmp_path = tmp.name
    spec = importlib.util.spec_from_file_location("harness_before", tmp_path)
    module = importlib.util.module_from_spec(spec)
    # Register before exec so the module's @dataclass type resolution
    # (which looks up sys.modules[cls.__module__]) works.
    sys.modules["harness_before"] = module
    spec.loader.exec_module(module)
    return module.AgentHarness().classify_intent


def _score(cases, classify):
    tp = fp = fn = tn = 0
    wrong = []
    preds = []
    for case in cases:
        actual = bool(case["needs_context"])
        pred = bool(classify(case["question"]).requires_project_context)
        preds.append(pred)
        if pred and actual:
            tp += 1
        elif pred and not actual:
            fp += 1
            wrong.append((case["question"], actual, pred))
        elif not pred and actual:
            fn += 1
            wrong.append((case["question"], actual, pred))
        else:
            tn += 1
    total = len(cases)
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "total": total,
        "wrong": wrong, "preds": preds,
    }


def _print_report(title, m):
    print(f"[{title}]")
    print(f"  정확도    : {m['tp'] + m['tn']}/{m['total']} = {m['accuracy']:.1%}")
    print(f"  Precision : {m['precision']:.3f}   (접근으로 라우팅한 것 중 실제로 필요했던 비율)")
    print(f"  Recall    : {m['recall']:.3f}   (접근이 필요한 것 중 제대로 잡은 비율)")
    print(f"  F1        : {m['f1']:.3f}")
    print("  혼동행렬 (양성 = 저장소 접근 필요)")
    print(f"                 예측 True   예측 False")
    print(f"     실제 True      {m['tp']:>3}         {m['fn']:>3}")
    print(f"     실제 False     {m['fp']:>3}         {m['tn']:>3}")
    if m["wrong"]:
        print(f"  오분류 {len(m['wrong'])}건:")
        for q, actual, pred in m["wrong"]:
            kind = "FP·불필요한 접근" if pred else "FN·조회 놓침"
            print(f"    - [{kind}] 정답={actual!s:5} 예측={pred!s:5} | {q}")
    print()


def main() -> None:
    data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    cases = data["cases"]
    pos = sum(1 for c in cases if c["needs_context"])
    print("=" * 60)
    print("의도 분류 정확도 평가")
    print(f"골든셋: {len(cases)}문항 (접근 필요 True={pos}, False={len(cases) - pos})")
    print("=" * 60)
    print()

    classify_after = _load_current_classifier()
    m_after = _score(cases, classify_after)
    _print_report("수정 후 · 현재 (정의성 예외 포함)", m_after)

    classify_before = _load_classifier_from_git(BEFORE_REV)
    if classify_before is None:
        print(f"(수정 전 분류기를 {BEFORE_REV}에서 불러오지 못해 비교를 건너뜁니다.)")
        return

    m_before = _score(cases, classify_before)
    _print_report(f"수정 전 · {BEFORE_REV} (정의성 예외 없음)", m_before)

    print("[수정 전 → 후 변화]")
    print(f"  정확도  : {m_before['accuracy']:.1%}  →  {m_after['accuracy']:.1%}"
          f"  ({m_after['accuracy'] - m_before['accuracy']:+.1%})")
    print(f"  Precision: {m_before['precision']:.3f}  →  {m_after['precision']:.3f}"
          f"  ({m_after['precision'] - m_before['precision']:+.3f})")
    print(f"  Recall  : {m_before['recall']:.3f}  →  {m_after['recall']:.3f}"
          f"  ({m_after['recall'] - m_before['recall']:+.3f})")
    print(f"  F1      : {m_before['f1']:.3f}  →  {m_after['f1']:.3f}"
          f"  ({m_after['f1'] - m_before['f1']:+.3f})")
    print()

    changed = [
        (c["question"], b, a, c["needs_context"])
        for c, b, a in zip(cases, m_before["preds"], m_after["preds"])
        if b != a
    ]
    if changed:
        print(f"[예측이 바뀐 문항] {len(changed)}건")
        for q, b, a, actual in changed:
            better = "개선" if (a == actual and b != actual) else (
                "악화" if (a != actual and b == actual) else "변화")
            print(f"    - {b!s:5} → {a!s:5} (정답 {actual!s:5}) [{better}] | {q}")


if __name__ == "__main__":
    main()
