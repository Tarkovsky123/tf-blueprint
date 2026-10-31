"""결함 심기 시험: 문서의 정답 표시와 tf.py check 결과를 대조한다.

정답 표시: 위반이 있는 줄 끝의 <!-- expect: 코드[, 코드] -->, 필수 절 누락은 첫 줄 meta의 missing=개수.
사용: python bench/run_bench.py [세트 폴더 ...]   (기본: sources.csv가 있는 bench/ 아래 모든 세트)
결과: 화면 요약 + bench/results.md
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tf  # noqa: E402

EXPECT = re.compile(r"\s*<!--\s*expect:\s*([A-Z_,\s]+?)\s*-->")
META = re.compile(r"<!--\s*meta:\s*(.*?)\s*-->")


def parse(path: Path):
    raw = path.read_text(encoding="utf-8")
    meta = dict(kv.split("=", 1) for kv in META.search(raw).group(1).split())
    expected, lines = Counter(), []
    for n, line in enumerate(raw.splitlines(), 1):
        m = EXPECT.search(line)
        if m:
            for code in m.group(1).split(","):
                expected[(n, code.strip())] += 1
            line = EXPECT.sub("", line)
        lines.append(line)
    expected[(0, "SECTION_MISSING")] += int(meta.get("missing", 0))
    return meta, "\n".join(lines), +expected


def run(set_dir: Path):
    sources = tf.load_sources(set_dir / "sources.csv")
    rows = []
    for p in sorted(set_dir.glob("*.md")):
        meta, text, expected = parse(p)
        found = Counter()
        for f in tf.check_text(text, p.name, meta["mode"], sources, meta["final"] == "true"):
            found[(0, f.code) if f.code == "SECTION_MISSING" else (f.line, f.code)] += 1
        rows.append({"file": p.name, "tp": expected & found, "fn": expected - found, "fp": found - expected})
    return rows


def summarize(rows):
    tp = sum(sum(r["tp"].values()) for r in rows)
    fn = sum(sum(r["fn"].values()) for r in rows)
    fp = sum(sum(r["fp"].values()) for r in rows)
    codes = Counter()
    for r in rows:
        for kind in ("tp", "fn", "fp"):
            for (_, code), n in r[kind].items():
                codes[(code, kind)] += n
    return tp, fn, fp, codes


def report(name, rows) -> list[str]:
    tp, fn, fp, codes = summarize(rows)
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    out = [f"## {name}", "",
           f"문서 {len(rows)}개 · 정답 결함 {tp + fn}개 · 맞게 잡음 {tp} · 놓침 {fn} · 잘못 잡음 {fp}",
           f"정밀도 {prec:.1%} · 재현율 {rec:.1%}", "",
           "| 코드 | 맞게 잡음 | 놓침 | 잘못 잡음 |", "|---|---|---|---|"]
    for code in sorted({c for c, _ in codes}):
        out.append(f"| {code} | {codes[(code, 'tp')]} | {codes[(code, 'fn')]} | {codes[(code, 'fp')]} |")
    if fn or fp:
        out += ["", "어긋난 곳:"]
        for r in rows:
            for kind, label in (("fn", "놓침"), ("fp", "잘못 잡음")):
                for (line, code), n in sorted(r[kind].items()):
                    out.append(f"- {r['file']}:{line or '-'} {code} {label}" + (f" ×{n}" if n > 1 else ""))
    return out + [""]


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sets = [Path(a) for a in (argv or sys.argv[1:])] or sorted(p.parent for p in HERE.glob("*/sources.csv"))
    lines = ["# 결함 심기 시험 결과", "", "`python bench/run_bench.py`가 만든다. 정답 표시와 `tf.py check` 결과를 줄 단위로 대조한다.", ""]
    for s in sets:
        lines += report(s.name, run(s))
    text = "\n".join(lines)
    (HERE / "results.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
