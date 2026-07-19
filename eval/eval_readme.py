"""README 갱신 필터(should_update_readme)의 정확도 평가.

각 케이스의 (diff, changed_files, commit_messages)를 3단 캐스케이드에 넣어
"README 갱신 필요" 판정을 골든셋과 비교한다. 양성(positive) = 갱신 필요(True).
  - False Positive = 갱신 불필요한데 갱신으로 판정 (불필요한 PR 유발)
  - False Negative = 갱신 필요한데 스킵 (문서가 뒤처짐)

또한 각 판정이 어느 층에서 끝났는지(layer1 규칙 / layer2 정규식 / layer3 LLM)를
집계한다. "전체 중 layer3(LLM)까지 간 비율"이 낮을수록 캐스케이드가 비용을
아끼고 있다는 뜻 -- 이 설계의 효율을 보여주는 지표.

layer3는 실제 작은 모델(gpt-4o-mini)을 호출하므로 OPENAI_API_KEY가 필요하다.
(.env에서 읽는다.) 애매한 케이스에서만 호출된다.

실행: python eval/eval_readme.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

from eval.readme_golden import CASES  # noqa: E402
from github_ai_agent.readme_updater import should_update_readme  # noqa: E402


def _deciding_layer(trace: dict) -> str:
    if trace["layer1"].get("hard_skip"):
        return "layer1"
    if trace.get("layer2") and trace["layer2"].get("verdict") in ("update", "skip"):
        return "layer2"
    if trace.get("layer3") is not None:
        return "layer3"
    return "unknown"


def main() -> None:
    load_dotenv(REPO_ROOT / ".env", override=True, encoding="utf-8-sig")
    client = OpenAI()

    tp = fp = fn = tn = 0
    layer_counts = {"layer1": 0, "layer2": 0, "layer3": 0, "unknown": 0}
    rows = []

    for case in CASES:
        actual = bool(case["needs_readme"])
        try:
            pred, trace = should_update_readme(
                case["diff"], case["changed_files"], case["commit_messages"], client
            )
        except Exception as error:  # layer3 LLM 호출 실패 등
            rows.append((case["name"], actual, None, f"오류: {error}"))
            continue
        layer = _deciding_layer(trace)
        layer_counts[layer] += 1
        if pred and actual:
            tp += 1
        elif pred and not actual:
            fp += 1
        elif not pred and actual:
            fn += 1
        else:
            tn += 1
        rows.append((case["name"], actual, pred, layer))

    total_scored = tp + fp + fn + tn
    accuracy = (tp + tn) / total_scored if total_scored else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    pos = sum(1 for c in CASES if c["needs_readme"])

    print("=" * 60)
    print("README 갱신 필터 정확도 평가")
    print(f"골든셋: {len(CASES)}건 (갱신 필요 True={pos}, False={len(CASES) - pos})")
    print("=" * 60)
    print()
    print("[판정 결과]")
    print(f"  정확도    : {tp + tn}/{total_scored} = {accuracy:.1%}")
    print(f"  Precision : {precision:.3f}   (갱신으로 판정한 것 중 실제 필요했던 비율)")
    print(f"  Recall    : {recall:.3f}   (갱신 필요한 것 중 제대로 잡은 비율)")
    print(f"  F1        : {f1:.3f}")
    print("  혼동행렬 (양성 = 갱신 필요)")
    print("                 예측 True   예측 False")
    print(f"     실제 True      {tp:>3}         {fn:>3}")
    print(f"     실제 False     {fp:>3}         {tn:>3}")
    print()
    print("[캐스케이드 효율 - 어느 층에서 판정이 끝났나]")
    for layer in ("layer1", "layer2", "layer3", "unknown"):
        n = layer_counts[layer]
        if layer == "unknown" and n == 0:
            continue
        label = {
            "layer1": "layer1 규칙(LLM 없음)",
            "layer2": "layer2 정규식(LLM 없음)",
            "layer3": "layer3 작은 모델(LLM 호출)",
            "unknown": "미상",
        }[layer]
        pct = n / total_scored if total_scored else 0.0
        print(f"  {label:26} {n:>2}건 ({pct:.0%})")
    no_llm = layer_counts["layer1"] + layer_counts["layer2"]
    print(f"  → LLM 없이 판정: {no_llm}/{total_scored} = "
          f"{(no_llm / total_scored if total_scored else 0):.0%}")
    print()
    print("[문항별]")
    for name, actual, pred, info in rows:
        if pred is None:
            print(f"  ?  {name}  ({info})")
            continue
        mark = "OK" if pred == actual else "XX"
        print(f"  {mark} 정답={actual!s:5} 예측={pred!s:5} [{info:6}] | {name}")


if __name__ == "__main__":
    main()
