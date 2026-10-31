"""예시 TF 두 개를 다시 만든다(회사·숫자·출처는 모두 가상). 사용: python examples/build_examples.py

각 예시 폴더에 TF 전체와 brief.txt(수석 비서 브리핑), check.txt(품질 점검 결과)가 생긴다.
"""
import io
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tf  # noqa: E402


def run(root, today, *argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            tf.main(["--dir", str(root), "--today", today, *argv])
        except SystemExit as e:  # check가 오류를 찾으면 1로 끝난다. 결과는 그대로 남긴다
            if e.code not in (0, 1, None):
                raise
    return buf.getvalue()


def charter(root, rows):
    path = root / "TF.md"
    text = path.read_text(encoding="utf-8")
    for value in rows:
        text = text.replace("(작성)", value, 1)
    path.write_text(text, encoding="utf-8")


def consulting():
    root = HERE / "consulting-demo"
    shutil.rmtree(root, ignore_errors=True)
    tf.main(["--today", "2026-11-02", "new", "가상 인화지 유통사 거래처 유지 전략", "--mode", "consulting",
             "--deadline", "2026-11-13", "--path", str(root)])
    charter(root, [
        "상위 거래처 이탈을 막아 내년 매출을 지키려면 무엇부터 해야 하나?",
        "거래처 수는 유지되지만 상위 거래처의 재주문 간격이 길어지고 있다",
        "대표(영업 총괄) / 독자: 경영진",
        "실행안 3개 이내, 각 안에 대상 거래처·담당·기대 효과·확인 지표가 있다",
        "B2B 거래처 유지 / 제외: 신규 거래처 확보, 가격 정책 전면 개편",
        "2026-10-31까지의 사내 판매 데이터",
        "2주, 사내 판매 데이터만 사용, 외부 설문 없음",
        "① 영업: 현장에서 돌아가나? ② 재무: 매출 효과는 얼마인가? ③ 경영진: 왜 지금인가?",
        "거래처별 월 매출(대표가 전달), 업계 공개 통계",
    ])
    d = "2026-11-02"
    run(root, d, "need", "add", "거래처별 월 매출 파일(최근 24개월)", "--owner", "lead", "--why", "매출 집중도·재주문 주기 계산")
    run(root, d, "need", "add", "업계 출하량 공개 통계", "--owner", "ai", "--why", "시장 추세와 비교")
    run(root, d, "source", "--title", "가상 거래처별 월 매출(사내)", "--publisher", "가상 유통사",
        "--date", "2026-10", "--locator", "시트 '거래처별' A1:Z420", "--status", "✅", "--note", "예시용 가상 자료")
    run(root, d, "source", "--title", "가상 업계 출하량 통계", "--publisher", "가상 협회",
        "--url", "https://example.com/stat", "--date", "2026-09", "--locator", "8쪽 표2", "--status", "⚠️",
        "--note", "예시용 가상 자료")
    for t in ("T01", "T02", "T03"):
        run(root, d, "task", "done", t)
    run(root, d, "gate", "approve", "G0", "--quote", "헌장 이대로 갑시다")
    run(root, "2026-11-04", "task", "done", "T04")
    run(root, "2026-11-04", "hyp", "add", "재주문 간격이 평소보다 길어진 상위 거래처가 이탈 위험이 높다")
    run(root, "2026-11-04", "hyp", "add", "이탈 위험 거래처에 먼저 방문하면 재주문이 회복된다")
    run(root, "2026-11-04", "task", "done", "T05")
    run(root, "2026-11-04", "task", "add", "주문 간격과 이후 구매 감소의 관계 분석", "--hyp", "H1", "--stage", "2")
    run(root, "2026-11-04", "task", "add", "방문 거래처와 미방문 거래처의 재주문 비교 설계", "--hyp", "H2", "--stage", "2")
    run(root, "2026-11-04", "event", "add", "2026-11-09", "대표 중간보고(스토리라인 초안)")
    run(root, "2026-11-04", "raid", "add", "거래처 매출 파일이 늦게 오면 진단이 하루 밀린다",
        "--kind", "dependency", "--level", "high", "--owner", "lead")
    run(root, "2026-11-04", "raid", "add", "재주문 간격 45일 초과를 이탈 신호로 본다",
        "--kind", "assumption", "--level", "mid")
    run(root, "2026-11-04", "decide", "신규 확보보다 상위 거래처 유지부터 다룬다",
        "--why", "상위 거래처가 매출의 대부분을 차지(가상 데이터)", "--quote", "유지 먼저 봅시다")
    draft = root / "work" / "drafts" / "diagnosis.md"
    draft.write_text("\n".join([
        "# 진단 초안",
        "",
        "## SCQA",
        "",
        "상위 거래처 82곳이 매출의 64%를 낸다 [S1].",
        "업계 출하량은 3년째 줄었다 [S2].",
        "재주문 간격이 길어진 거래처는 1년 안에 30% 넘게 이탈한다.",
        "",
        "## Day-1 가설",
        "",
        "재주문 간격이 길어지는 거래처를 먼저 찾아 방문하면 이탈을 줄일 수 있다 [가정].",
        "",
    ]), encoding="utf-8")
    run(root, "2026-11-04", "log", "SCQA·이슈트리 끝, 가설 2개 등록 / 대표: 거래처 매출 파일 전달 / 다음: Day-1 가설 검증 방법")
    (root / "brief.txt").write_text(run(root, "2026-11-05", "brief"), encoding="utf-8")
    (root / "check.txt").write_text(run(root, "2026-11-05", "check"), encoding="utf-8")


MODEL = '''"""가상소재 추정 모델 (예시용 가상 숫자). 실행: python work/model.py"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
shipments = 1050      # 2027년 출하량, 백만㎡ [가정]
price = 565           # 평균 단가, 원/㎡ [가정]
margin = 0.199        # 영업이익률 [가정]
consensus_op = 1050   # 시장 기대 영업이익, 억 원 (출처 S2)
shares = 2480         # 주식 수, 만 주
per = 14              # 목표 주가수익비율 [가정]

revenue = shipments * price / 100          # 억 원
op = revenue * margin                      # 억 원
eps = op * 0.78 * 1e4 / shares             # 원 (세후 78% 가정)
print(f"영업이익 {op:,.0f}억 원, 시장 기대 대비 {op / consensus_op - 1:+.0%}")
print(f"적정 주가 {eps * per:,.0f}원")
'''


def research():
    root = HERE / "research-demo"
    shutil.rmtree(root, ignore_errors=True)
    tf.main(["--today", "2026-11-02", "new", "가상소재 커버리지 개시", "--mode", "research",
             "--deadline", "2026-11-20", "--path", str(root)])
    charter(root, [
        "가상소재의 분리막 물량 회복이 2027년 이익을 시장 기대보다 끌어올리나?",
        "단가 하락으로 시장 기대가 낮아졌지만 고객사 증설 발표가 이어지고 있다",
        "대표(개인 학습용 분석) / 독자: 대표 본인",
        "과거 숫자 100% 공시 대조, 시나리오 3개와 확률 표현, 논지가 깨지는 조건 명시",
        "분리막 사업 / 제외: 다른 사업부, 단기 주가 예측",
        "2026-11-02 종가, 2025년 사업보고서",
        "3주, 공개 자료만, 투자 권유 아님",
        "① 단가 하락이 더 깊으면? ② 증설이 늦어지면? ③ 이미 주가에 반영됐다면?",
        "사업보고서(AI가 수집), 업계 리포트 요약(대표가 구함)",
    ])
    d = "2026-11-02"
    run(root, d, "source", "--title", "가상 사업보고서 2025", "--publisher", "가상소재",
        "--locator", "45쪽 사업부별 매출", "--status", "✅", "--note", "예시용 가상 자료")
    run(root, d, "source", "--title", "가상 고객사 증설 발표·증권사 컨센서스 요약", "--publisher", "가상 고객사",
        "--locator", "보도자료 2문단", "--status", "⚠️", "--note", "예시용 가상 자료")
    run(root, d, "source", "--title", "가상 업계 블로그 추정치", "--status", "❓", "--note", "확인 전")
    for t in ("T01", "T02", "T03"):
        run(root, d, "task", "done", t)
    run(root, d, "gate", "approve", "G0", "--quote", "좋습니다, 시작하죠")
    run(root, d, "hyp", "add", "고객사 증설 물량이 단가 하락을 상쇄한다")
    run(root, d, "event", "add", "2027-02-10", "4분기 실적 발표(물량 회복 첫 확인)")
    (root / "work" / "model.py").write_text(MODEL, encoding="utf-8")
    shutil.copy2(root / "blueprint" / "templates" / "final_research.md", root / "work" / "final" / "report.md")
    report = root / "work" / "final" / "report.md"
    text = report.read_text(encoding="utf-8")
    fills = {
        "# (작성: 대상) — (작성: 한 줄 논지)": "# 가상소재 — 물량 회복이 단가 하락을 이긴다",
        "(작성: 의견·핵심 논지·핵심 숫자)": "2027년 영업이익은 1,180억 원으로 시장 기대보다 12% 높다고 본다 [추정].",
        "(작성: 시장은 X라고 본다 → 우리는 Y라고 본다 → 근거)":
            "시장은 단가 하락이 이어진다고 본다 [S1]. 우리는 고객사 증설로 물량이 이를 상쇄한다고 본다 [S2].",
        "(작성: 핵심 추정치마다 시장 기대 [S번호] · 우리 추정 [추정: work/모델파일] · 차이(%), 전제는 [가정])":
            "시장 기대 영업이익은 1,050억 원이다 [S2]. 우리 추정은 1,181억 원으로 12% 높다 [추정: work/model.py]. "
            "블로그 추정 출하량은 1,000백만㎡다 [S3].",
        "(작성: 방법, 가정, 결과)": "목표 주가수익비율 14배 [가정], 적정 주가 51,983원 [계산: work/model.py].",
        "(작성: 날짜 · 이벤트 · 논지에 주는 의미)": "2027-02-10 4분기 실적 발표 · 물량 회복 첫 확인",
        "## 6. 리스크\n\n(작성)": "## 6. 리스크\n\n증설이 반년 늦어지면 이익 추정이 낮아진다. 그럴 가능성은 아마 낮다.",
        "## 7. 논지가 깨지는 조건\n\n(작성)": "## 7. 논지가 깨지는 조건\n\n출하량이 두 분기 연속 전년보다 줄면 의견을 내린다.",
        "이해상충: (작성)": "이해상충: 없음",
    }
    for k, v in fills.items():
        text = text.replace(k, v)
    report.write_text(text, encoding="utf-8")
    (root / "brief.txt").write_text(run(root, "2026-11-06", "brief"), encoding="utf-8")
    (root / "check.txt").write_text(run(root, "2026-11-06", "check"), encoding="utf-8")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with redirect_stdout(io.StringIO()):
        consulting()
        research()
    for name in ("consulting-demo", "research-demo"):
        print(f"── {name}/brief.txt\n" + (HERE / name / "brief.txt").read_text(encoding="utf-8"))
        print(f"── {name}/check.txt\n" + (HERE / name / "check.txt").read_text(encoding="utf-8"))
