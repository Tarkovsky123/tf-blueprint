#!/usr/bin/env python3
"""TF 청사진 관리 프로그램.

날짜·마감·관문 순서·출처 대조처럼 틀리면 안 되는 일은 이 프로그램이 하고,
판단·반론·글쓰기는 AI(수석 비서이자 노련한 파트너)가 한다.
표준 라이브러리만 쓴다(Python 3.10+). 명령 목록: python tf.py -h
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEEK = "월화수목금토일"
STATUS_START = "<!-- tf:status:start"
STATUS_END = "<!-- tf:status:end -->"
AUTO_HEAD = "## 4. 수석 비서 기록 (자동)"
WHO = {"ai": "AI", "lead": "대표"}
LEVELS = {"high": "높음", "mid": "중간", "low": "낮음"}
RAID_KINDS = {"risk": "리스크", "assumption": "가정", "issue": "이슈", "dependency": "의존"}
HYP = {"open": "검증 중", "supported": "지지", "rejected": "기각"}
SOON = 14  # 브리핑에 띄울 다가오는 일정의 범위(일)

# 팀 방식별 단계. weight는 기간 배분 비율, criteria는 관문 메모의 통과 기준이다.
MODES = {
    "consulting": {
        "label": "컨설팅",
        "playbook": "consulting.md",
        "final_gate": 3,
        "first_section": ["결론", "요약", "핵심"],
        "sections": [["결론", "요약", "핵심"], ["근거", "분석"],
                     ["실행", "로드맵", "다음 단계", "액션"], ["리스크", "한계"]],
        "stages": [
            {"name": "착수", "weight": 1, "gate": "TF 헌장 승인",
             "tasks": ["TF 헌장 작성(인터뷰)", "자료 요청 목록 작성", "레드팀 관점 3개 정하기"],
             "criteria": ["목적과 최종 의사결정자가 한 문장으로 적혀 있다",
                          "성공 기준마다 합격선(숫자나 확인 방법)이 있다",
                          "범위·제외 범위·기준 시점·마감이 정해졌다",
                          "대표가 구할 자료와 AI가 모을 자료가 나뉘었다"]},
            {"name": "진단", "weight": 2, "gate": "문제 정의·핵심 가설",
             "tasks": ["SCQA 문제 정의", "이슈트리(MECE)와 가설 등록(hyp add)", "Day-1 가설과 검증 방법",
                       "고스트 덱 초안(헤드라인만)", "우선순위·가지치기"],
             "criteria": ["문제가 SCQA 한 문단으로 정리됐다",
                          "이슈트리가 겹침·누락 없이 나뉘었고 가설이 등록됐다",
                          "가설마다 검증 방법과 필요한 자료가 있다",
                          "고스트 덱 초안(헤드라인만)이 있다",
                          "버릴 가지와 그 이유가 적혔다"]},
            {"name": "분석", "weight": 3, "gate": "스토리라인(채운 고스트 덱)",
             "tasks": ["가설별 워크플랜(task add --hyp)", "자료 수집·출처 기록", "핵심 분석(숫자는 코드로)",
                       "사전 부검", "고스트 덱을 분석 결과로 채우기"],
             "criteria": ["가설마다 지지·기각·검증 중 상태가 기록됐다",
                          "헤드라인만 읽어도 이야기가 서고, 헤드라인마다 근거 분석이 연결됐다",
                          "사전 부검에서 나온 실패 원인마다 대응이 있다",
                          "열린 리스크와 가정이 대표에게 보고됐다"]},
            {"name": "작성·QA", "weight": 3, "gate": "최종본",
             "tasks": ["본문 작성", "출처·숫자 점검(tf.py check --final)", "레드팀 3관점 리뷰(work/redteam.md)",
                       "지적 반영"],
             "criteria": ["tf.py check --final 오류 0건",
                          "레드팀 지적마다 반영했거나 반영하지 않은 이유가 있다",
                          "성공 기준마다 본문 위치가 있다",
                          "가정은 [가정]으로 표시됐다"]},
            {"name": "버퍼·전달", "weight": 1, "gate": "전달 완료",
             "tasks": ["최종 확인·전달", "회고(tf.py close)"],
             "criteria": ["최종본이 전달됐다", "회고와 교훈이 기록됐다"]},
        ],
    },
    "research": {
        "label": "증권사 리서치",
        "playbook": "research.md",
        "final_gate": 3,
        "first_section": ["요약", "투자 논지", "핵심"],
        "sections": [["논지"], ["컨센서스", "시장 기대"], ["가치평가", "밸류에이션"], ["리스크"], ["촉매"],
                     ["깨지는 조건", "깨짐", "철회 조건"], ["고지", "면책"]],
        "stages": [
            {"name": "착수", "weight": 1, "gate": "TF 헌장 승인",
             "tasks": ["TF 헌장 작성(대상·질문·기준 시점·독자)", "자료 요청 목록(공시·IR·업계 자료)",
                       "레드팀 관점 3개 정하기"],
             "criteria": ["분석 대상과 답할 질문이 한 문장으로 적혀 있다",
                          "성공 기준마다 합격선이 있다",
                          "기준 시점(자료·가격 기준일)과 마감이 정해졌다",
                          "대표가 구할 자료와 AI가 모을 자료가 나뉘었다"]},
            {"name": "기업·산업 이해", "weight": 2, "gate": "논지 가설",
             "tasks": ["사업 구조·매출 구성(공시 원문)", "핵심 변수 트리", "시장 기대(컨센서스) 정리",
                       "논지 기둥을 가설로 등록(hyp add)"],
             "criteria": ["시장 기대가 출처와 함께 정리됐다",
                          "논지가 시장 기대와 어디서 다른지 한 문장으로 말할 수 있다",
                          "논지를 좌우하는 핵심 변수가 3개 이내로 정해졌다",
                          "논지가 깨지는 조건이 미리 적혔다"]},
            {"name": "모델·검증", "weight": 3, "gate": "모델 리뷰",
             "tasks": ["재무 추정 모델(코드나 시트)", "시나리오(낙관·기준·비관)", "공시 원문과 숫자 대조",
                       "핵심 가정 점검", "사전 부검"],
             "criteria": ["모델의 과거 숫자가 공시 원문과 일치한다",
                          "추정치마다 모델 파일을 가리키는 [추정: 파일] 표시가 있다",
                          "시나리오마다 결과와 확률 표현이 있다",
                          "핵심 가정 점검과 사전 부검 결과가 반영됐다"]},
            {"name": "리포트·심의", "weight": 3, "gate": "발간 심의",
             "tasks": ["리포트 작성", "출처·숫자 점검(tf.py check --final)", "반대 논리 레드팀(work/redteam.md)",
                       "이해상충·미공개정보·고지 확인"],
             "criteria": ["tf.py check --final 오류 0건",
                          "반대 논리에 대한 답이 본문에 있다",
                          "미공개 중요정보를 쓰지 않았다(모든 출처가 공개 자료)",
                          "이해상충 여부와 '투자 권유 아님' 고지가 있다"]},
            {"name": "발간·사후관리", "weight": 1, "gate": "발간 완료",
             "tasks": ["발간", "촉매 일정 등록(event add)과 논지 점검 주기", "회고(tf.py close)"],
             "criteria": ["발간됐다", "다가오는 촉매가 일정(event)으로 등록됐다", "회고가 기록됐다"]},
        ],
    },
}


# ── 날짜 ──────────────────────────────────────────────

def d(x) -> date:
    return x if isinstance(x, date) else date.fromisoformat(x)


def parse_date(s, what="날짜") -> date:
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        raise SystemExit(f"{what} 형식이 틀렸습니다: {s} (YYYY-MM-DD로 쓰세요)") from None


def fmt(x) -> str:
    x = d(x)
    return f"{x.month:02d}/{x.day:02d}({WEEK[x.weekday()]})"


def dday(target, today) -> str:
    n = (d(target) - today).days
    return "D-day" if n == 0 else (f"D-{n}" if n > 0 else f"D+{-n}(지남)")


def waited(since, today) -> str:
    n = (today - d(since)).days
    return "오늘 요청" if n <= 0 else f"요청 {n}일째"


def plan(start: date, deadline: date, weights: list[int]) -> list[tuple[date, date]]:
    """비율대로 단계 기간을 나눈다. 마지막 단계는 마감에 끝난다."""
    if deadline < start:
        raise SystemExit("마감이 시작일보다 빠릅니다.")
    total, s, cum, out, prev = (deadline - start).days, sum(weights), 0, [], None
    for w in weights:
        cum += w
        end = start + timedelta(days=int(cum / s * total + 0.5))
        begin = start if prev is None else min(prev + timedelta(days=1), end)
        out.append((begin, end))
        prev = end
    out[-1] = (out[-1][0], deadline)
    return out


# ── 상태 ──────────────────────────────────────────────

def new_state(name, mode, start: date, deadline: date, lead) -> dict:
    m = MODES[mode]
    windows = plan(start, deadline, [s["weight"] for s in m["stages"]])
    stages, tasks = [], []
    for i, (spec, (b, e)) in enumerate(zip(m["stages"], windows)):
        stages.append({"id": i, "name": spec["name"], "start": b.isoformat(), "end": e.isoformat(),
                       "gate": {"id": f"G{i}", "name": spec["gate"], "status": "open",
                                "requested": None, "decided": None, "quote": "", "note": ""}})
        for t in spec["tasks"]:
            tasks.append({"id": f"T{len(tasks) + 1:02d}", "title": t, "stage": i, "owner": "ai",
                          "due": e.isoformat(), "status": "open", "done": None, "hyp": None, "note": ""})
    return {"version": 2, "name": name, "mode": mode, "lead": lead,
            "start": start.isoformat(), "deadline": deadline.isoformat(), "closed": None,
            "stages": stages, "tasks": tasks, "decisions": [], "raid": [], "needs": [],
            "hyps": [], "events": [], "log": [], "updated": None}


def next_id(items, prefix) -> str:
    nums = [int(x["id"][len(prefix):]) for x in items if x["id"].startswith(prefix)]
    return f"{prefix}{max(nums, default=0) + 1:02d}"


def current_stage(st):
    for s in st["stages"]:
        if s["gate"]["status"] != "approved":
            return s["id"]
    return None


def find(items, key, what):
    canon = lambda s: re.sub(r"^([A-Z]+)0*(?=\d)", r"\1", s.strip().upper())  # noqa: E731  H1 = H01
    for x in items:
        if canon(x["id"]) == canon(key):
            return x
    raise SystemExit(f"{what} {key}를 찾을 수 없습니다.")


def find_root(arg) -> Path:
    if arg:
        return Path(arg).resolve()
    for p in (HERE, Path.cwd(), *Path.cwd().parents):
        if (p / "tf" / "state.json").exists():
            return p
    raise SystemExit("TF 폴더가 아닙니다. 먼저 python tf.py new ... 로 만드세요(또는 --dir).")


def load(root: Path) -> dict:
    st = json.loads((root / "tf" / "state.json").read_text(encoding="utf-8"))
    for key in ("hyps", "events", "log"):  # 이전 판(version 1) 상태 파일도 읽는다
        st.setdefault(key, [])
    return st


def save(root: Path, st: dict, today: date):
    st["updated"] = today.isoformat()
    (root / "tf" / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
    render(root, st, today)


def record(st, today, text, why="", quote=""):
    st["decisions"].append({"id": next_id(st["decisions"], "D"), "date": today.isoformat(),
                            "text": text, "why": why, "quote": quote})


def open_tasks(st):
    return [t for t in st["tasks"] if t["status"] == "open"]


def hyp_summary(st) -> str:
    parts = []
    for h in st["hyps"]:
        mine = [t for t in st["tasks"] if t.get("hyp") == h["id"] and t["status"] != "dropped"]
        done = sum(t["status"] == "done" for t in mine)
        parts.append(f"{h['id']} {HYP[h['status']]}" + (f"(할 일 {done}/{len(mine)})" if mine else ""))
    return " · ".join(parts)


# ── 출처 ──────────────────────────────────────────────

SRC_FIELDS = ["id", "title", "publisher", "date", "url", "locator", "status", "checked", "note"]
SRC_STATUS = {"✅": "✅", "verified": "✅", "⚠️": "⚠️", "⚠": "⚠️", "single": "⚠️",
              "❓": "❓", "unverified": "❓", "": "❓"}


def load_sources(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        if r.get("id"):
            r["status"] = SRC_STATUS.get((r.get("status") or "").strip(), "❓")
            out[r["id"].strip().upper()] = r
    return out


def source_stats(sources: dict) -> str:
    c = {k: sum(1 for r in sources.values() if r["status"] == k) for k in ("✅", "⚠️", "❓")}
    return f"{len(sources)}건 (✅{c['✅']} ⚠️{c['⚠️']} ❓{c['❓']})"


# ── 품질 점검 ──────────────────────────────────────────

@dataclass
class Finding:
    path: str
    line: int
    level: str  # 오류 | 경고
    code: str
    msg: str


TAG = re.compile(r"\[(S\d+(?:\s*[,，]\s*S\d+)*)\]")
LABEL = re.compile(r"\[(가정|계산|추정)(?:\s*[:：]\s*([^\]]+?))?\s*\]")
NUM = re.compile(r"(?<![\w.,])([$₩€¥]\s?)?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?"
                 r"(\s?(?:%p|%|퍼센트포인트|퍼센트|bp|배|[억조만천]*(?:원|달러|엔|위안|유로|명|건|곳|개사|톤|가구)"
                 r"|[억조만천]+))?")
WORD_NUM = re.compile(r"(?<![가-힣])(?:두|세|네|다섯|여섯|일곱|여덟|아홉|열|수십|수백)\s?(?:배|퍼센트)")
# 숫자+한글 단위 뒤에 올 수 있는 조사·어미의 첫 글자. 그 밖의 한글이 붙으면 단위가 아니라 낱말이다(3원칙, 2배송).
PARTICLES = set("은는이가을를의에도로으과와만까부씩며대쯤정다였입일인라란미보밖뿐째짜여나남안내")
PLACEHOLDER = re.compile(r"TODO|TBD|FIXME|\?\?|\(작성\)|○○|〇〇")
HEDGE = re.compile(r"아마|어쩌면|일지도|것 같다|것 같습니다|듯하다|듯합니다|수도 있다|수도 있습니다"
                   r"|가능성이 있다|가능성이 있습니다|가능성이 있음|(?:것|으로|로) 보인다|(?:것|으로|로) 보입니다")
# 확률 표현: 척도의 말, 또는 "확률 70%"처럼 확률·가능성과 함께 쓴 숫자%. "15% 감소"의 %는 확률이 아니다.
PROB = re.compile(r"거의 확실|가능성(?:이|은|을)? ?(?:매우 )?(?:높|낮)|반반|거의 없|(?:확률|가능성)\D{0,6}\d+\s?%")
HANGUL = re.compile(r"[가-힣]")


def _is_word(text, end) -> bool:
    nxt = text[end:end + 1]
    return bool(HANGUL.match(nxt or " ")) and nxt not in PARTICLES


def claim_numbers(text: str) -> list[str]:
    found = []
    for m in NUM.finditer(text):
        cur, whole, frac, unit = m.groups()
        if not (cur or unit or frac or "," in whole):
            continue
        if unit and re.search("%|퍼센트", unit) and re.search(r"(?:확률|가능성)\D{0,6}$", text[:m.start()]):
            continue  # "확률 70%"는 출처가 필요한 사실이 아니라 판단이다
        if unit and HANGUL.match(unit.strip()[-1]) and _is_word(text, m.end()):
            continue
        found.append(m.group(0).strip())
    found += [m.group(0) for m in WORD_NUM.finditer(text) if not _is_word(text, m.end())]
    return found


def sentences(line: str) -> list[str]:
    out = []
    for p in re.split(r"(?<=[.!?。])\s+", line):
        rest = LABEL.sub("", TAG.sub("", p)).strip(" .,·()")
        if out and not rest:
            out[-1] += " " + p  # 꼬리에 붙은 [S3] 같은 표시는 앞 문장의 근거다
        else:
            out.append(p)
    return out


def content_lines(text: str):
    """코드 블록·주석·제목을 뺀 본문 줄을 (줄 번호, 줄, 표 근거 여부)로 낸다."""
    lines = text.splitlines()
    fence = comment = False
    table_ok = {}
    i = 0
    while i < len(lines):  # 표 안이나 표 바로 위·아래(빈 줄 건너) 줄에 출처가 있으면 표 전체가 근거를 가진다
        if lines[i].lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            above = next((x for x in reversed(lines[:i]) if x.strip()), "")
            below = next((x for x in lines[j:] if x.strip()), "")
            ok = any(TAG.search(x) or LABEL.search(x) for x in [above, below, *lines[i:j]])
            for k in range(i, j):
                table_ok[k] = ok
            i = j
        else:
            i += 1
    for n, line in enumerate(lines):
        s = line.strip()
        if s.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if comment or s.startswith("<!--"):
            comment = "-->" not in s  # 닫는 표시가 나올 때까지 주석 안이다
            continue
        if s.startswith("#") or not s:
            continue
        yield n + 1, line, table_ok.get(n, False)


def check_text(text, rel, mode, sources, final, root: Path | None = None) -> list[Finding]:
    """root를 주면 [계산: 파일]의 파일이 실제로 있는지도 본다."""
    out, no_locator = [], set()
    level = "오류" if final else "경고"
    for n, line, table_ok in content_lines(text):
        for m in TAG.finditer(line):
            for sid in re.split(r"\s*[,，]\s*", m.group(1)):
                sid = sid.upper()
                if sid not in sources:
                    out.append(Finding(rel, n, "오류", "SRC_UNKNOWN", f"출처 목록에 없는 {sid}"))
                elif sources[sid]["status"] == "❓":
                    out.append(Finding(rel, n, level, "SRC_UNVERIFIED", f"{sid}가 ❓미확인 상태"))
                elif final and not (sources[sid].get("locator") or "").strip() and sid not in no_locator:
                    no_locator.add(sid)
                    out.append(Finding(rel, n, "경고", "SRC_NOLOCATOR",
                                       f"{sid}에 쪽·표 위치(locator)가 없음 — 출처 목록에 적기"))
        for m in LABEL.finditer(line):
            kind, ref = m.group(1), (m.group(2) or "").strip()
            if ref and root is not None and not (root / ref).exists():
                out.append(Finding(rel, n, "오류", "CALC_MISSING", f"[{kind}: {ref}]의 파일이 없음"))
            elif final and not ref and kind in ("계산", "추정"):
                out.append(Finding(rel, n, "경고", "CALC_NOFILE",
                                   f"[{kind}]이 어느 파일에서 나왔는지 적기 — 예: [{kind}: work/model.py]"))
        if final and PLACEHOLDER.search(line):
            out.append(Finding(rel, n, "오류", "PLACEHOLDER",
                               f"덜 쓴 표시가 남음: {PLACEHOLDER.search(line).group(0)}"))
        for sent in sentences(line):
            nums = claim_numbers(sent)
            if nums and not table_ok and not (TAG.search(sent) or LABEL.search(sent)):
                out.append(Finding(rel, n, level, "NUM_NOSRC",
                                   f"근거 표시 없는 숫자 {nums[0]} ([S번호]나 [가정]·[계산]·[추정] 필요)"))
            if final and HEDGE.search(sent) and not PROB.search(sent):
                out.append(Finding(rel, n, "경고", "HEDGE",
                                   f"'{HEDGE.search(sent).group(0)}' — 확률 표현(가능성 높음 등)으로 바꾸기"))
    if final:
        out += check_structure(text, rel, mode)
    return out


def check_structure(text, rel, mode) -> list[Finding]:
    m = MODES[mode]
    lines = text.splitlines()
    heads = [(n + 1, ln.lstrip("#").strip()) for n, ln in enumerate(lines) if re.match(r"#{2,3}\s", ln)]
    out = []
    h2 = [(n, h) for n, h in heads if lines[n - 1].startswith("## ")]
    if h2 and not any(k in h2[0][1] for k in m["first_section"]):
        out.append(Finding(rel, h2[0][0], "오류", "ANSWER_NOT_FIRST",
                           f"첫 절이 '{h2[0][1]}' — 결론을 먼저({'/'.join(m['first_section'])})"))
    for group in m["sections"]:
        if not any(k in h for _, h in heads for k in group):
            out.append(Finding(rel, 1, "오류", "SECTION_MISSING", f"필수 절 없음: {'/'.join(group)}"))
    return out


def check_files(paths, root: Path, mode, sources, final) -> list[Finding]:
    out = []
    for p in paths:
        try:
            rel = str(p.relative_to(root)).replace("\\", "/")
        except ValueError:
            rel = str(p)
        out += check_text(p.read_text(encoding="utf-8"), rel, mode, sources, final, root)
    return out


def tf_check(root: Path, st: dict) -> tuple[list[Finding], list[Finding]]:
    sources = load_sources(root / "tf" / "sources.csv")
    drafts = sorted((root / "work" / "drafts").rglob("*.md"))
    finals = sorted((root / "work" / "final").rglob("*.md"))
    return (check_files(drafts, root, st["mode"], sources, False),
            check_files(finals, root, st["mode"], sources, True))


def blanks(path: Path, root: Path, marker="(작성") -> list[str]:
    """덜 채운 줄의 위치. TF.md의 상태판 부분은 보지 않는다."""
    text = path.read_text(encoding="utf-8").split(STATUS_START)[0]
    rel = path.relative_to(root).as_posix()
    return [f"{rel}:{n}" for n, ln in enumerate(text.splitlines(), 1) if marker in ln]


def gate_blockers(root: Path, st: dict, i: int, today: date) -> list[str]:
    """관문 i의 승인을 막는 것을 모두 모은다."""
    out = [f"단계 할 일이 남음: {t['id']} {t['title']} (끝내거나 task drop {t['id']} --why로 취소)"
           for t in open_tasks(st) if t["stage"] == i]
    if i == 0:
        out += [f"헌장 빈칸: {b}" for b in blanks(root / "TF.md", root, "(작성)")]
        return out
    memo = root / "work" / "gates" / f"G{i}.md"
    if not memo.exists():
        out.append(f"관문 메모가 없습니다. 먼저 gate request G{i}로 만들고 채우세요")
    else:
        out += [f"관문 메모 빈칸: {b}" for b in blanks(memo, root)]
    mode = MODES[st["mode"]]
    if i == mode["final_gate"]:
        if not list((root / "work" / "final").rglob("*.md")):
            out.append("work/final/에 최종본(.md)이 없습니다")
        else:
            _, finals = tf_check(root, st)
            out += [f"{f.path}:{f.line} {f.code} {f.msg}" for f in finals if f.level == "오류"]
        red = root / "work" / "redteam.md"
        if not red.exists():
            out.append("레드팀 기록이 없습니다: tf.py doc redteam으로 만들고 채우세요")
        else:
            out += [f"레드팀 빈칸: {b}" for b in blanks(red, root)]
    if st["mode"] == "research" and i == len(st["stages"]) - 1:
        if not [e for e in st["events"] if e["status"] == "open" and d(e["date"]) >= today]:
            out.append("다가오는 촉매 일정이 없습니다: tf.py event add YYYY-MM-DD \"...\"")
    return out


# ── 화면 ──────────────────────────────────────────────

def gate_mark(g) -> str:
    return {"approved": f"✅ {fmt(g['decided'])} 승인" if g["decided"] else "✅",
            "requested": "⏳ 대표 결정 대기", "rejected": "↩ 반려·재작업"}.get(g["status"], "□")


def status_block(root: Path, st: dict, today: date) -> str:
    cur = current_stage(st)
    count = {k: sum(t["status"] == k for t in st["tasks"]) for k in ("open", "done", "dropped")}
    late = [t for t in open_tasks(st) if d(t["due"]) < today]
    risks = [r for r in st["raid"] if r["status"] == "open"]
    needs = [n for n in st["needs"] if n["status"] == "open" and n["from"] == "lead"]
    soon = sorted(e["date"] for e in st["events"] if e["status"] == "open" and d(e["date"]) >= today)
    src = load_sources(root / "tf" / "sources.csv")
    stage = (f"{cur} {st['stages'][cur]['name']} → 다음 관문 G{cur} {st['stages'][cur]['gate']['name']}"
             if cur is not None else "모든 관문 통과")
    rows = [
        f"{STATUS_START} (tf.py가 고침. 직접 고치지 않는다) -->",
        "| 항목 | 상태 |", "|---|---|",
        f"| 기준일 | {fmt(today)} · 마감 {fmt(st['deadline'])} {dday(st['deadline'], today)} |",
        f"| 현재 단계 | {stage} |",
        f"| 할 일 | 남음 {count['open']} · 완료 {count['done']} · 취소 {count['dropped']} · 지연 {len(late)} |",
        f"| 가설 | {hyp_summary(st) or '없음'} |",
        f"| 다가오는 일정 | {len(soon)}건" + (f" (가장 가까운 {fmt(soon[0])})" if soon else "") + " |",
        f"| 대표에게 요청한 자료 | 열림 {len(needs)} |",
        f"| 리스크·가정·이슈 | 열림 {len(risks)} (높음 {sum(r['level'] == 'high' for r in risks)}) |",
        f"| 출처 | {source_stats(src)} |",
        "", "| 단계 | 기간 | 관문 | 상태 |", "|---|---|---|---|",
    ]
    for s in st["stages"]:
        rows.append(f"| {s['id']} {s['name']} | {fmt(s['start'])}–{fmt(s['end'])} | "
                    f"G{s['id']} {s['gate']['name']} | {gate_mark(s['gate'])} |")
    rows.append(STATUS_END)
    return "\n".join(rows)


def render(root: Path, st: dict, today: date):
    tf = root / "TF.md"
    if not tf.exists():
        return
    text = tf.read_text(encoding="utf-8")
    block = status_block(root, st, today)
    if STATUS_START in text and STATUS_END in text:
        head, rest = text.split(STATUS_START, 1)
        text = head + block + rest.split(STATUS_END, 1)[1]
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    tf.write_text(text, encoding="utf-8")


def brief(root: Path, st: dict, today: date) -> str:
    m = MODES[st["mode"]]
    cur = current_stage(st)
    out = [f"[수석 비서 브리핑] {fmt(today)} · 「{st['name']}」({m['label']}) · "
           f"마감 {fmt(st['deadline'])} {dday(st['deadline'], today)}"]
    if st["log"]:
        last = st["log"][-1]
        out.append(f"지난 세션 인계 ({fmt(last['date'])}): {last['text']}")
    if st.get("closed"):
        out.append(f"이 TF는 {fmt(st['closed'])}에 종료됐습니다.")
        retro = root / "work" / "retro.md"
        if retro.exists() and blanks(retro, root):
            out.append("지금 할 일:\n 1. 회고 양식(work/retro.md) 채우기 (AI 초안 → 대표 확인)")
        return "\n".join(out)
    actions = []
    if cur is None:
        out.append("단계: 모든 관문 통과 — tf.py close로 종료하고 회고를 쓴다")
    else:
        s, g = st["stages"][cur], st["stages"][cur]["gate"]
        out.append(f"단계: {cur} {s['name']} (~{fmt(s['end'])}, {dday(s['end'], today)}) · "
                   f"다음 관문: G{cur} {g['name']} [{gate_mark(g)}]")
        mine = [t for t in st["tasks"] if t["stage"] == cur and t["status"] != "dropped"]
        span = (d(s["end"]) - d(s["start"])).days + 1
        elapsed = min(max((today - d(s["start"])).days, 0), span) / span  # 다 지난 날만 센다
        done = sum(t["status"] == "done" for t in mine) / len(mine) if mine else 1
        if today > d(s["end"]):
            out.append(f"⚠ 일정: 이 단계의 관문 예정일이 {(today - d(s['end'])).days}일 지났습니다 "
                       "(범위를 줄일지, tf.py replan으로 마감을 옮길지 대표에게 묻는다)")
        elif elapsed >= 0.5 and done + 0.3 < elapsed:
            out.append(f"⚠ 일정: 단계 기간의 {elapsed:.0%}가 지났는데 할 일은 {done:.0%} 완료")
    for s in st["stages"]:
        g = s["gate"]
        if g["status"] == "requested":
            actions.append(f"G{s['id']} {g['name']} 승인 여부 결정 (대표, {waited(g['requested'], today)}) "
                           f"— 메모 work/gates/G{s['id']}.md")
    late = sorted((t for t in open_tasks(st) if d(t["due"]) < today), key=lambda t: t["due"])
    due = [t for t in open_tasks(st) if d(t["due"]) == today]
    lead_needs = [n for n in st["needs"] if n["status"] == "open" and n["from"] == "lead"]
    ai_needs = [n for n in st["needs"] if n["status"] == "open" and n["from"] == "ai"]
    events = sorted((e for e in st["events"] if e["status"] == "open"), key=lambda e: e["date"])
    past = [e for e in events if d(e["date"]) < today]
    soon = [e for e in events if 0 <= (d(e["date"]) - today).days <= SOON]
    risks = sorted((r for r in st["raid"] if r["status"] == "open"),
                   key=lambda r: ["high", "mid", "low"].index(r["level"]))
    if late:
        out.append(f"늦어진 일 ({len(late)}): " + " · ".join(
            f"{t['id']} {t['title']}({WHO[t['owner']]}, {(today - d(t['due'])).days}일 지남)" for t in late))
    if due:
        out.append(f"오늘 마감 ({len(due)}): " + " · ".join(f"{t['id']} {t['title']}" for t in due))
    if soon:
        out.append(f"다가오는 일정 ({SOON}일 안): " + " · ".join(
            f"{e['id']} {fmt(e['date'])} {e['text']} ({dday(e['date'], today)})" for e in soon))
    if past:
        out.append("지난 일정, 결과 기록 필요: " + " · ".join(f"{e['id']} {fmt(e['date'])} {e['text']}" for e in past))
    if lead_needs:
        out.append(f"대표에게 요청한 자료 ({len(lead_needs)}): " + " · ".join(
            f"{n['id']} {n['what']}({waited(n['date'], today)})" for n in lead_needs))
    if ai_needs:
        out.append(f"AI가 모을 자료 ({len(ai_needs)}): " + " · ".join(f"{n['id']} {n['what']}" for n in ai_needs))
    if st["hyps"]:
        out.append(f"가설: {hyp_summary(st)}")
    if risks:
        out.append(f"열린 리스크·가정·이슈 ({len(risks)}): " + " · ".join(
            f"{r['id']} [{RAID_KINDS[r['kind']]}·{LEVELS[r['level']]}] {r['text']}" for r in risks[:3]))
    src = load_sources(root / "tf" / "sources.csv")
    if src:
        out.append(f"출처: {source_stats(src)}")
    if st.get("updated") and (today - d(st["updated"])).days >= 2:
        out.append(f"⚠ 상태판이 {(today - d(st['updated'])).days}일째 갱신되지 않았습니다")
    actions += [f"{t['id']} {t['title']} 마무리 ({WHO[t['owner']]})" for t in late]
    actions += [f"{e['id']} {e['text']} 결과 기록 (AI) — tf.py event done {e['id']} --why \"...\"" for e in past]
    actions += [f"{n['id']} {n['what']} 전달 (대표, {waited(n['date'], today)})" for n in lead_needs]
    actions += [f"{t['id']} {t['title']} ({WHO[t['owner']]}, 오늘 마감)" for t in due]
    if cur is not None:
        mine = [t for t in open_tasks(st) if t["stage"] == cur]
        if not mine and st["stages"][cur]["gate"]["status"] in ("open", "rejected"):
            actions.append(f"G{cur} 관문 메모 준비 (AI) — python tf.py gate request G{cur}")
        actions += [f"{t['id']} {t['title']} ({WHO[t['owner']]}, ~{fmt(t['due'])})"
                    for t in sorted(mine, key=lambda t: t["due"])]
    seen = []
    for a in actions:
        if a not in seen:
            seen.append(a)
    if seen:
        out.append("지금 할 일:")
        out += [f" {i}. {a}" for i, a in enumerate(seen[:3], 1)]
    return "\n".join(out)


def write_memo(root: Path, st: dict, i: int, today: date) -> Path:
    """관문 메모를 만든다. 이미 있으면(반려 뒤 재요청) 1~3절은 두고 요청일과 4절(자동 기록)만 새로 쓴다."""
    path = root / "work" / "gates" / f"G{i}.md"
    s, spec = st["stages"][i], MODES[st["mode"]]["stages"][i]
    mine = [t for t in st["tasks"] if t["stage"] == i]
    left = [f"{t['id']} {t['title']}" for t in mine if t["status"] == "open"]
    dropped = [f"{t['id']}({t['note']})" for t in mine if t["status"] == "dropped"]
    risks = [f"{r['id']} {r['text']}" for r in st["raid"] if r["status"] == "open"]
    needs = [f"{n['id']} {n['what']}" for n in st["needs"] if n["status"] == "open"]
    drafts, finals = tf_check(root, st)
    errs = sum(f.level == "오류" for f in drafts + finals)
    request = f"요청 {fmt(today)} · 단계 {i} {s['name']} ({fmt(s['start'])}–{fmt(s['end'])})"
    auto = "\n".join([
        AUTO_HEAD, "",
        f"- 이 단계 할 일: 완료 {sum(t['status'] == 'done' for t in mine)}/{len(mine)}"
        + (f" · 남음: {', '.join(left)}" if left else "") + (f" · 취소: {', '.join(dropped)}" if dropped else ""),
        f"- 가설: {hyp_summary(st) or '없음'}",
        f"- 열린 리스크·가정·이슈: {', '.join(risks) or '없음'}",
        f"- 열린 자료 요청: {', '.join(needs) or '없음'}",
        f"- 출처: {source_stats(load_sources(root / 'tf' / 'sources.csv'))}",
        f"- 품질 점검(tf.py check): 오류 {errs} · 경고 {len(drafts + finals) - errs}", ""])
    if path.exists():
        text = re.sub(r"^요청 .*$", lambda _: request, path.read_text(encoding="utf-8"), count=1, flags=re.M)
        if AUTO_HEAD in text:
            text = re.sub(re.escape(AUTO_HEAD) + r".*?(?=\n## |\Z)", lambda _: auto.rstrip("\n"), text,
                          count=1, flags=re.S)
        else:
            text = text.rstrip() + "\n\n" + auto
    else:
        text = "\n".join([
            f"# G{i} {spec['gate']} — 관문 메모", "", request, "",
            "## 1. 대표가 정할 것", "", "(작성: 승인·반려·조건부 승인 중 무엇을, 무엇을 근거로)", "",
            "## 2. 파트너 의견", "", "(작성: 추천 하나와 이유 2~3개, 가장 약한 고리, 반대 의견)", "",
            "## 3. 통과 기준", "", *[f"- [ ] {c}" for c in spec["criteria"]], "", auto])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ── 명령 ──────────────────────────────────────────────

def cmd_new(args, today):
    if args.mode not in MODES:
        raise SystemExit(f"--mode는 {', '.join(MODES)} 중 하나")
    dest = Path(args.path).resolve()
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest}가 비어 있지 않습니다.")
    start = parse_date(args.start, "--start") if args.start else today
    deadline = parse_date(args.deadline, "--deadline")
    st = new_state(args.name, args.mode, start, deadline, args.lead)
    bp, m = HERE / "blueprint", MODES[args.mode]
    for sub in ("tf", "work/gates", "work/drafts", "work/final", "blueprint/templates"):
        (dest / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).resolve(), dest / "tf.py")
    for f in ("common.md", m["playbook"]):
        shutil.copy2(bp / f, dest / "blueprint" / f)
    for f in (bp / "templates").glob("*.md"):
        if f.name not in ("TF.md", "AGENTS.md"):
            shutil.copy2(f, dest / "blueprint" / "templates" / f.name)
    subs = {"{{name}}": args.name, "{{mode}}": m["label"], "{{playbook}}": m["playbook"],
            "{{start}}": fmt(start), "{{deadline}}": fmt(deadline), "{{lead}}": args.lead}
    for f in ("TF.md", "AGENTS.md"):
        text = (bp / "templates" / f).read_text(encoding="utf-8")
        for k, v in subs.items():
            text = text.replace(k, v)
        (dest / f).write_text(text, encoding="utf-8")
    (dest / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    with (dest / "tf" / "sources.csv").open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(SRC_FIELDS)
    save(dest, st, today)
    print(f"TF를 만들었습니다: {dest}")
    print(brief(dest, st, today))


def cmd_gate(root, st, args, today):
    s = find([x["gate"] | {"_i": x["id"]} for x in st["stages"]], args.gate, "관문")
    i = s["_i"]
    g = st["stages"][i]["gate"]
    if args.action == "request":
        if g["status"] == "approved":
            raise SystemExit(f"G{i}는 이미 승인됐습니다.")
        g["status"], g["requested"] = "requested", today.isoformat()
        path = write_memo(root, st, i, today)
        save(root, st, today)
        print(f"G{i} 결정 요청을 기록했습니다. 메모: {path.relative_to(root)}")
        return
    if not args.quote:
        raise SystemExit("대표가 채팅에서 한 말을 --quote로 남기세요. 대표의 말 없이 관문을 넘기지 않습니다.")
    earlier = [f"G{x['id']}" for x in st["stages"][:i] if x["gate"]["status"] != "approved"]
    if earlier:
        raise SystemExit(f"관문 순서 위반: {', '.join(earlier)}가 아직 승인되지 않았습니다.")
    if args.action == "approve":
        blockers = gate_blockers(root, st, i, today)
        if blockers:
            print(f"G{i} 통과를 막는 것 {len(blockers)}건:")
            print("\n".join(f" - {b}" for b in blockers))
            if not args.force:
                raise SystemExit(1)
            if not args.note:
                raise SystemExit("--force로 넘길 때는 --note에 이유를 남기세요.")
        g.update(status="approved", decided=today.isoformat(), quote=args.quote, note=args.note or "")
        text = f"G{i} {g['name']} 승인" + (" (막는 것을 알고 넘김)" if blockers else "")
    else:
        if not args.note:
            raise SystemExit("반려할 때는 --note에 이유를 남기세요. 이유를 할 일로 바꿔 재작업한다.")
        g.update(status="rejected", decided=today.isoformat(), quote=args.quote, note=args.note)
        text = f"G{i} {g['name']} 반려"
    record(st, today, text, args.note or "", args.quote)
    save(root, st, today)
    print(f"{text} — 기록했습니다.")


def cmd_task(root, st, args, today):
    if args.action == "add":
        if not args.text:
            raise SystemExit("할 일 내용을 쓰세요: task add \"...\"")
        cur = current_stage(st)
        stage = args.stage if args.stage is not None else (cur if cur is not None else len(st["stages"]) - 1)
        if not 0 <= stage < len(st["stages"]):
            raise SystemExit(f"--stage는 0~{len(st['stages']) - 1} 중 하나")
        hyp = find(st["hyps"], args.hyp, "가설")["id"] if args.hyp else None
        due = parse_date(args.due, "--due") if args.due else d(st["stages"][stage]["end"])
        t = {"id": next_id(st["tasks"], "T"), "title": args.text, "stage": stage, "owner": args.owner,
             "due": due.isoformat(), "status": "open", "done": None,
             "hyp": hyp, "note": ""}
        st["tasks"].append(t)
        print(f"{t['id']} 추가: {t['title']} ({WHO[t['owner']]}, ~{fmt(t['due'])})"
              + (f" · 가설 {t['hyp']}" if t["hyp"] else ""))
    elif args.action in ("done", "drop"):
        t = find(st["tasks"], args.text, "할 일")
        if args.action == "drop":
            if not args.why:
                raise SystemExit("취소할 때는 --why에 이유를 남기세요.")
            t.update(status="dropped", done=today.isoformat(), note=args.why)
            print(f"{t['id']} 취소: {t['title']} — {args.why}")
        else:
            t.update(status="done", done=today.isoformat())
            print(f"{t['id']} 완료: {t['title']}")
    else:
        for t in open_tasks(st):
            print(f"{t['id']} [{t['stage']}단계·{WHO[t['owner']]}] {t['title']} ~{fmt(t['due'])}"
                  + (f" · {t['hyp']}" if t.get("hyp") else ""))
        return
    save(root, st, today)


def cmd_hyp(root, st, args, today):
    if args.action == "add":
        h = {"id": next_id(st["hyps"], "H"), "text": args.text, "status": "open",
             "date": today.isoformat(), "note": ""}
        st["hyps"].append(h)
        print(f"{h['id']} 가설 등록: {h['text']}")
    else:
        h = find(st["hyps"], args.text, "가설")
        if args.status not in HYP:
            raise SystemExit(f"--status는 {', '.join(HYP)} 중 하나 ({', '.join(HYP.values())})")
        h.update(status=args.status, note=args.why or "")
        record(st, today, f"{h['id']} {HYP[args.status]}: {h['text']}", args.why or "")
        print(f"{h['id']} → {HYP[args.status]}")
    save(root, st, today)


def cmd_event(root, st, args, today):
    if args.action == "add":
        when = parse_date(args.key, "일정 날짜")
        if not args.text:
            raise SystemExit("일정 내용을 쓰세요: event add YYYY-MM-DD \"...\"")
        e = {"id": next_id(st["events"], "E"), "date": when.isoformat(), "text": args.text,
             "status": "open", "note": ""}
        st["events"].append(e)
        print(f"{e['id']} 일정: {fmt(e['date'])} {e['text']}")
    else:
        e = find(st["events"], args.key, "일정")
        e.update(status="done", note=args.why or "")
        print(f"{e['id']} 결과 기록: {e['text']}" + (f" — {args.why}" if args.why else ""))
    save(root, st, today)


def cmd_need(root, st, args, today):
    if args.action == "add":
        n = {"id": next_id(st["needs"], "N"), "what": args.text, "from": args.owner, "why": args.why or "",
             "status": "open", "date": today.isoformat(), "done": None, "note": ""}
        st["needs"].append(n)
        print(f"{n['id']} 자료 요청: {n['what']} ({'대표가 구함' if n['from'] == 'lead' else 'AI가 모음'})")
    else:
        n = find(st["needs"], args.text, "자료 요청")
        n.update(status="done", done=today.isoformat(), note=args.why or "")
        print(f"{n['id']} 받음: {n['what']}")
    save(root, st, today)


def cmd_raid(root, st, args, today):
    if args.action == "add":
        if args.kind not in RAID_KINDS:
            raise SystemExit(f"--kind는 {', '.join(RAID_KINDS)} 중 하나")
        r = {"id": next_id(st["raid"], "R"), "kind": args.kind, "text": args.text, "level": args.level,
             "owner": args.owner, "status": "open", "date": today.isoformat(), "note": ""}
        st["raid"].append(r)
        print(f"{r['id']} [{RAID_KINDS[r['kind']]}·{LEVELS[r['level']]}] {r['text']}")
    else:
        r = find(st["raid"], args.text, "기록")
        r.update(status="closed", note=args.why or "")
        print(f"{r['id']} 닫음")
    save(root, st, today)


def cmd_decide(root, st, args, today):
    record(st, today, args.text, args.why or "", args.quote or "")
    save(root, st, today)
    print(f"{st['decisions'][-1]['id']} 결정 기록: {args.text}")


def cmd_log(root, st, args, today):
    st["log"].append({"date": today.isoformat(), "text": args.text})
    save(root, st, today)
    print("세션 인계를 남겼습니다. 다음 브리핑 맨 위에 나옵니다.")


def cmd_replan(root, st, args, today):
    if not args.quote:
        raise SystemExit("마감 변경은 대표가 정한다. 대표의 말을 --quote로 남기세요.")
    new = parse_date(args.deadline, "--deadline")
    cur = current_stage(st)
    if cur is None:
        raise SystemExit("모든 관문이 끝나 다시 짤 단계가 없습니다.")
    begin = max(today, d(st["stages"][cur]["start"]))
    if new < begin:
        raise SystemExit(f"새 마감이 {fmt(begin)}보다 빠릅니다.")
    old_end = {s["id"]: s["end"] for s in st["stages"]}
    weights = [MODES[st["mode"]]["stages"][s["id"]]["weight"] for s in st["stages"][cur:]]
    for s, (b, e) in zip(st["stages"][cur:], plan(begin, new, weights)):
        if s["id"] != cur:  # 이미 시작한 현재 단계는 시작일을 그대로 둔다
            s["start"] = b.isoformat()
        s["end"] = e.isoformat()
    moved = 0
    for t in open_tasks(st):  # 단계 끝에 맞춰 둔 할 일만 따라 옮긴다. 따로 정한 날짜는 그대로
        if t["stage"] >= cur and t["due"] == old_end[t["stage"]]:
            t["due"] = st["stages"][t["stage"]]["end"]
            moved += 1
    old = st["deadline"]
    st["deadline"] = new.isoformat()
    record(st, today, f"마감 변경 {fmt(old)} → {fmt(new)}", args.why or "", args.quote)
    save(root, st, today)
    print(f"마감을 {fmt(old)} → {fmt(new)}로 바꾸고 단계 {cur}~{len(st['stages']) - 1}을 다시 배분했습니다"
          f"(할 일 {moved}개 마감일 이동).")


def cmd_doc(root, st, args, today):
    tpl = root / "blueprint" / "templates"
    names = sorted(p.stem for p in tpl.glob("*.md"))
    if args.name not in names:
        raise SystemExit(f"양식 이름: {', '.join(names)}")
    dest = root / "work" / ("final/report.md" if args.name.startswith("final_") else f"{args.name}.md")
    if dest.exists():
        raise SystemExit(f"{dest.relative_to(root)}가 이미 있습니다.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tpl / f"{args.name}.md", dest)
    print(f"{dest.relative_to(root)}를 만들었습니다. 빈칸 (작성...)을 채우세요.")


def cmd_source(root, st, args, today):
    path = root / "tf" / "sources.csv"
    src = load_sources(path)
    sid = f"S{max([int(k[1:]) for k in src if k[1:].isdigit()], default=0) + 1}"
    status = SRC_STATUS.get(args.status, None)
    if status is None:
        raise SystemExit("--status는 ✅(verified) ⚠️(single) ❓(unverified) 중 하나")
    header = SRC_FIELDS
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as f:
            header = next(csv.reader(f), SRC_FIELDS)
    row = {"id": sid, "title": args.title, "publisher": args.publisher or "", "date": args.date or "",
           "url": args.url or "", "locator": args.locator or "", "status": status,
           "checked": (parse_date(args.checked, "--checked") if args.checked else today).isoformat(),
           "note": args.note or ""}
    with path.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=header, extrasaction="ignore").writerow(row)
    save(root, st, today)
    print(f"[{sid}] {args.title} {status}")


def cmd_check(root, st, args, today):
    if args.paths:
        mode = args.mode or (st["mode"] if st else "consulting")
        sources = load_sources(Path(args.sources) if args.sources else root / "tf" / "sources.csv")
        found = check_files([Path(p).resolve() for p in args.paths], root, mode, sources, args.final)
    else:
        drafts, finals = tf_check(root, st)
        found = drafts + finals
    for f in found:
        print(f"{f.path}:{f.line} [{f.level}] {f.code} {f.msg}")
    errs = sum(f.level == "오류" for f in found)
    print(f"점검 결과: 오류 {errs} · 경고 {len(found) - errs}")
    if errs:
        raise SystemExit(1)


def cmd_close(root, st, args, today):
    gates = [s for s in st["stages"] if s["gate"]["status"] == "approved"]
    on_time = sum(d(s["gate"]["decided"]) <= d(s["end"]) for s in gates)
    done = [t for t in st["tasks"] if t["status"] == "done"]
    dropped = sum(t["status"] == "dropped" for t in st["tasks"])
    late = sum(d(t["done"]) > d(t["due"]) for t in done)
    path = root / "work" / "retro.md"
    path.write_text("\n".join([
        f"# 회고 — {st['name']}", "", f"종료 {fmt(today)} · 시작 {fmt(st['start'])} · 마감 {fmt(st['deadline'])}", "",
        "## 숫자 (자동)", "",
        f"- 관문: 승인 {len(gates)}/{len(st['stages'])}, 그중 예정일 안에 {on_time}",
        f"- 할 일: 완료 {len(done)}/{len(st['tasks'])}, 취소 {dropped}, 늦게 끝난 것 {late}",
        f"- 가설: {hyp_summary(st) or '없음'}",
        f"- 결정 기록 {len(st['decisions'])}건 · 리스크·가정·이슈 {len(st['raid'])}건 · 자료 요청 {len(st['needs'])}건"
        f" · 일정 {len(st['events'])}건",
        f"- 출처: {source_stats(load_sources(root / 'tf' / 'sources.csv'))}", "",
        "## 하려던 것과 실제로 일어난 것", "", "(작성)", "", "## 차이가 난 이유", "", "(작성)", "",
        "## 다음 TF에 가져갈 규칙", "", "(작성: 규칙 한 줄 + 이번에 생긴 일 + 적용할 곳)", ""]), encoding="utf-8")
    st["closed"] = today.isoformat()
    save(root, st, today)
    print(f"TF를 종료했습니다. 회고 양식: {path.relative_to(root)}")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="tf.py", description="TF 청사진: 상태판·관문·기록·품질 점검")
    ap.add_argument("--dir", help="TF 폴더(기본: tf.py가 있는 폴더나 현재 폴더)")
    ap.add_argument("--today", help="기준일 YYYY-MM-DD(기본: 오늘)")
    common = argparse.ArgumentParser(add_help=False)  # --dir·--today는 명령 뒤에 써도 된다
    common.add_argument("--dir", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    common.add_argument("--today", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, help_text):
        return sub.add_parser(name, help=help_text, parents=[common])

    p = add("new", "새 TF 폴더 만들기")
    p.add_argument("name")
    p.add_argument("--mode", required=True, help="consulting | research")
    p.add_argument("--deadline", required=True)
    p.add_argument("--start")
    p.add_argument("--lead", default="대표")
    p.add_argument("--path", required=True, help="만들 폴더")

    add("brief", "수석 비서 브리핑")
    add("render", "TF.md 상태판 다시 그리기")

    p = add("gate", "관문: request | approve | reject")
    p.add_argument("action", choices=["request", "approve", "reject"])
    p.add_argument("gate")
    p.add_argument("--quote", help="대표가 채팅에서 한 말(승인·반려에 필수)")
    p.add_argument("--note", help="반려 이유, 강행 이유")
    p.add_argument("--force", action="store_true")

    p = add("task", "할 일: add | done | drop | list")
    p.add_argument("action", choices=["add", "done", "drop", "list"])
    p.add_argument("text", nargs="?", default="")
    p.add_argument("--stage", type=int)
    p.add_argument("--due")
    p.add_argument("--owner", choices=["ai", "lead"], default="ai")
    p.add_argument("--hyp", help="이 할 일이 검증하는 가설(H1 등)")
    p.add_argument("--why", help="취소 이유(drop에 필수)")

    p = add("hyp", "가설: add | set")
    p.add_argument("action", choices=["add", "set"])
    p.add_argument("text", help="add: 가설 문장 / set: 가설 번호")
    p.add_argument("--status", help="open(검증 중) | supported(지지) | rejected(기각)")
    p.add_argument("--why")

    p = add("event", "일정(촉매·중간보고): add 날짜 내용 | done 번호")
    p.add_argument("action", choices=["add", "done"])
    p.add_argument("key", help="add: YYYY-MM-DD / done: 일정 번호")
    p.add_argument("text", nargs="?", default="")
    p.add_argument("--why", help="결과")

    p = add("need", "자료 요청: add | done")
    p.add_argument("action", choices=["add", "done"])
    p.add_argument("text")
    p.add_argument("--owner", choices=["ai", "lead"], default="lead", help="누가 구하나")
    p.add_argument("--why")

    p = add("raid", "리스크·가정·이슈·의존: add | close")
    p.add_argument("action", choices=["add", "close"])
    p.add_argument("text")
    p.add_argument("--kind", default="risk", help="risk | assumption | issue | dependency")
    p.add_argument("--level", choices=list(LEVELS), default="mid")
    p.add_argument("--owner", choices=["ai", "lead"], default="ai")
    p.add_argument("--why")

    p = add("decide", "결정 기록")
    p.add_argument("text")
    p.add_argument("--why")
    p.add_argument("--quote")

    p = add("log", "세션 인계(오늘 바뀐 것 / 대표가 정할 것 / 다음 첫 행동)")
    p.add_argument("text")

    p = add("replan", "마감 변경과 남은 단계 재배분(대표 결정)")
    p.add_argument("--deadline", required=True)
    p.add_argument("--why")
    p.add_argument("--quote", help="대표가 채팅에서 한 말(필수)")

    p = add("doc", "양식을 work/로 복사(redteam, premortem, final_research 등)")
    p.add_argument("name")

    p = add("source", "출처 추가")
    p.add_argument("--title", required=True)
    p.add_argument("--url")
    p.add_argument("--publisher")
    p.add_argument("--date")
    p.add_argument("--locator", help="쪽·표·절 위치")
    p.add_argument("--checked", help="원문 확인일(기본: 오늘)")
    p.add_argument("--status", default="❓")
    p.add_argument("--note")

    p = add("check", "품질 점검(출처·숫자·필수 절·덜 쓴 표시)")
    p.add_argument("paths", nargs="*")
    p.add_argument("--final", action="store_true")
    p.add_argument("--mode")
    p.add_argument("--sources")

    add("close", "TF 종료와 회고 양식")

    args = ap.parse_args(argv)
    today = parse_date(args.today, "--today") if args.today else date.today()
    if args.cmd == "new":
        return cmd_new(args, today)
    if args.cmd == "check" and args.paths:
        root = Path(args.dir).resolve() if args.dir else Path.cwd()
        st = load(root) if (root / "tf" / "state.json").exists() else None
        return cmd_check(root, st, args, today)
    root = find_root(args.dir)
    st = load(root)
    if args.cmd == "brief":
        print(brief(root, st, today))
    elif args.cmd == "render":
        render(root, st, today)
        print("TF.md 상태판을 다시 그렸습니다.")
    else:
        globals()[f"cmd_{args.cmd}"](root, st, args, today)


if __name__ == "__main__":
    main()
