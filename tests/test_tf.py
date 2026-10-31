"""실행: python -m unittest discover -s tests -v   (표준 라이브러리만)"""
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench"))
import run_bench  # noqa: E402
import tf  # noqa: E402

SOURCES = {"S1": {"status": "✅", "locator": "3쪽 표2"}, "S2": {"status": "⚠️", "locator": ""},
           "S7": {"status": "❓", "locator": ""}}
STRUCTURE = ("SECTION_MISSING", "ANSWER_NOT_FIRST")


def run(*argv) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        tf.main([str(a) for a in argv])
    return buf.getvalue()


def codes(text, mode="consulting", final=False, structure=True, root=None):
    found = tf.check_text(text, "x.md", mode, SOURCES, final, root)
    return [(f.line, f.code, f.level) for f in found if structure or f.code not in STRUCTURE]


class PlanTest(unittest.TestCase):
    def test_stages_cover_start_to_deadline(self):
        start = date(2026, 11, 1)
        for days in (0, 1, 2, 4, 9, 30, 90):
            windows = tf.plan(start, start + timedelta(days), [1, 2, 3, 3, 1])
            self.assertEqual(windows[0][0], start)
            self.assertEqual(windows[-1][1], start + timedelta(days))
            ends = [e for _, e in windows]
            self.assertEqual(ends, sorted(ends), days)
            self.assertTrue(all(b <= e for b, e in windows), days)

    def test_deadline_before_start_is_rejected(self):
        with self.assertRaises(SystemExit):
            tf.plan(date(2026, 11, 5), date(2026, 11, 1), [1, 1])


class NumberTest(unittest.TestCase):
    def test_factual_numbers(self):
        cases = {
            "매출 807억 원": ["807억"], "매출 807억을 기록": ["807억"], "점유율은 86%다": ["86%"],
            "4명이 운영": ["4명"], "3배로 늘었다": ["3배"], "2배였다": ["2배"], "$12.5다": ["$12.5"],
            "1,234개": ["1,234"], "평균 3.5": ["3.5"], "3만원": ["3만원"], "1.2%p 올랐다": ["1.2%p"],
            "점유율은 30퍼센트다": ["30퍼센트"], "2퍼센트포인트 올랐다": ["2퍼센트포인트"],
            "매출이 두 배로 늘었다": ["두 배"], "세배 늘었다": ["세배"],
        }
        for text, want in cases.items():
            self.assertEqual(tf.claim_numbers(text), want, text)

    def test_not_factual_numbers(self):
        for text in ("2026년 계획", "11/4까지", "2026-11-04", "G2 관문", "[S12] 참고", "T07 완료",
                     "제3자 검토", "3가지 이유", "2단계", "3원칙", "2배송 물류", "v3.10 기준", "1. 첫째",
                     "세 배송지", "확률 70%로 본다"):
            self.assertEqual(tf.claim_numbers(text), [], text)


class CheckTest(unittest.TestCase):
    def test_source_tag_covers_its_sentence_only(self):
        self.assertEqual(codes("매출은 10억 원이다 [S1]."), [])
        self.assertEqual(codes("매출은 10억 원이다. [S1]"), [])  # 꼬리 표시는 앞 문장의 근거
        found = codes("매출은 10억 원이다 [S1]. 이익은 2억 원이다.")
        self.assertEqual([c for _, c, _ in found], ["NUM_NOSRC"])

    def test_labels_count_as_basis(self):
        for label in ("[가정]", "[계산]", "[추정]", "[계산: work/a.py]"):
            self.assertEqual(codes(f"비용은 3억 원이다 {label}."), [], label)

    def test_level_depends_on_final(self):
        self.assertEqual(codes("비용은 3억 원이다.")[0][2], "경고")
        self.assertEqual(codes("비용은 3억 원이다.", final=True, structure=False)[0][2], "오류")

    def test_table_with_source_nearby(self):
        table = "| 항목 | 값 |\n|---|---|\n| 매출 | 1,200억 원 |\n"
        self.assertEqual([c for _, c, _ in codes(table)], ["NUM_NOSRC"])
        self.assertEqual(codes(table + "\n출처: [S1]"), [])
        self.assertEqual(codes("아래 표는 [S1] 기준.\n\n" + table), [])

    def test_code_blocks_headings_comments_are_skipped(self):
        text = "# 매출 10억 원\n```\nx = 10억 원\n```\n<!-- 10억 원 -->\n"
        self.assertEqual(codes(text), [])

    def test_sources(self):
        self.assertEqual(codes("근거 [S9]")[0][1:], ("SRC_UNKNOWN", "오류"))
        self.assertEqual(codes("근거 [S7]")[0][1:], ("SRC_UNVERIFIED", "경고"))
        self.assertEqual(codes("근거 [S7]", final=True, structure=False)[0][1:], ("SRC_UNVERIFIED", "오류"))
        self.assertEqual(codes("근거 [S1, S2]"), [])

    def test_locator_warning_once_per_source_in_final(self):
        found = codes("가 [S2].\n나 [S2].\n다 [S1].", final=True, structure=False)
        self.assertEqual(found, [(1, "SRC_NOLOCATOR", "경고")])
        self.assertEqual(codes("가 [S2]."), [])  # 초안은 보지 않는다

    def test_calc_labels_point_to_files(self):
        self.assertEqual(codes("값 [계산].", final=True, structure=False), [(1, "CALC_NOFILE", "경고")])
        self.assertEqual(codes("값 [계산]."), [])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(codes("값 [추정: work/m.py].", root=root), [(1, "CALC_MISSING", "오류")])
            (root / "work").mkdir()
            (root / "work" / "m.py").write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(codes("값 [추정: work/m.py].", final=True, structure=False, root=root), [])

    def test_placeholders_only_in_final(self):
        self.assertEqual(codes("TODO 나중에"), [])
        self.assertIn("PLACEHOLDER", [c for _, c, _ in codes("TODO 나중에", final=True)])

    def test_answer_first_and_sections(self):
        ok = "# 제목\n## 1. 결론\n답\n## 근거\n## 실행 계획\n## 리스크\n"
        self.assertEqual(codes(ok, final=True), [])
        late = "# 제목\n## 배경\n## 결론\n## 근거\n## 실행 계획\n## 리스크\n"
        self.assertEqual(codes(late, final=True), [(2, "ANSWER_NOT_FIRST", "오류")])
        found = tf.check_text("# 제목\n## 요약\n## 투자 논지\n", "x", "research", {}, True)
        missing = [f.msg for f in found if f.code == "SECTION_MISSING"]
        self.assertEqual(len(missing), 6)
        self.assertTrue(any("컨센서스" in m for m in missing))

    def test_hedge_needs_probability_words(self):
        hedge = lambda t: codes(t, final=True, structure=False)  # noqa: E731
        self.assertEqual(hedge("수요가 늘 것 같다."), [(1, "HEDGE", "경고")])
        self.assertEqual(hedge("수요가 늘 가능성이 있다."), [(1, "HEDGE", "경고")])
        self.assertEqual(hedge("수요가 늘 것으로 보인다."), [(1, "HEDGE", "경고")])
        self.assertEqual(hedge("수요가 늘 것 같다. 가능성 높음으로 본다."), [(1, "HEDGE", "경고")])
        self.assertEqual(hedge("수요가 늘 수도 있다(가능성 높음)."), [])
        self.assertEqual(hedge("성공할 것 같다(확률 70%)."), [])
        self.assertEqual(hedge("비용이 15% 줄 것 같다 [S1]."), [(1, "HEDGE", "경고")])  # 15%는 확률이 아니다
        self.assertEqual(codes("수요가 늘 것 같다."), [])  # 초안은 보지 않는다


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "tf1"
        run("--today", "2026-11-01", "new", "시험 TF", "--mode", "consulting",
            "--deadline", "2026-11-10", "--path", self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *argv, today="2026-11-01"):
        return run("--dir", self.root, "--today", today, *argv)

    def state(self):
        return json.loads((self.root / "tf" / "state.json").read_text(encoding="utf-8"))

    def fill(self, rel):
        path = self.root / rel
        path.write_text(path.read_text(encoding="utf-8").replace("(작성", "(채움"), encoding="utf-8")

    def finish_stage(self, i):
        for t in self.state()["tasks"]:
            if t["stage"] == i and t["status"] == "open":
                self.cli("task", "done", t["id"])

    def pass_gate(self, i):
        self.finish_stage(i)
        if i == 0:
            self.fill("TF.md")
        else:
            self.cli("gate", "request", f"G{i}")
            self.fill(f"work/gates/G{i}.md")
        self.cli("gate", "approve", f"G{i}", "--quote", "승인")

    def test_new_creates_a_self_contained_tf(self):
        for f in ("TF.md", "AGENTS.md", "CLAUDE.md", "tf.py", "tf/state.json", "tf/sources.csv",
                  "blueprint/common.md", "blueprint/consulting.md", "blueprint/templates/premortem.md"):
            self.assertTrue((self.root / f).exists(), f)
        self.assertEqual((self.root / "CLAUDE.md").read_text(encoding="utf-8").strip(), "@AGENTS.md")
        agents = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("「시험 TF」", agents)
        self.assertNotIn("{{", agents)
        self.assertIn("기준 시점", (self.root / "TF.md").read_text(encoding="utf-8"))
        self.assertIn("locator", (self.root / "tf" / "sources.csv").read_text(encoding="utf-8"))
        st = self.state()
        self.assertEqual(len(st["stages"]), 5)
        self.assertEqual(st["stages"][-1]["end"], "2026-11-10")
        self.assertEqual(len(st["tasks"]), 19)
        self.assertIn("고스트 덱 초안", [t["title"] for t in st["tasks"] if t["stage"] == 1][3])
        with self.assertRaises(SystemExit):  # 비어 있지 않은 폴더에는 만들지 않는다
            run("new", "또", "--mode", "consulting", "--deadline", "2026-11-10", "--path", self.root)

    def test_gates_need_quote_order_tasks_and_charter(self):
        with self.assertRaises(SystemExit):
            self.cli("gate", "approve", "G0")  # 대표의 말 없음
        with self.assertRaises(SystemExit):
            self.cli("gate", "approve", "G1", "--quote", "좋아요")  # G0 전
        with self.assertRaises(SystemExit):
            self.cli("gate", "approve", "G0", "--quote", "좋아요")  # 할 일 남음 + 헌장 빈칸
        self.fill("TF.md")
        with self.assertRaises(SystemExit):
            self.cli("gate", "approve", "G0", "--quote", "좋아요")  # 할 일 남음
        self.finish_stage(0)
        self.cli("gate", "approve", "G0", "--quote", "헌장 좋아요, 승인")
        st = self.state()
        self.assertEqual(st["stages"][0]["gate"]["status"], "approved")
        self.assertEqual(st["decisions"][-1]["quote"], "헌장 좋아요, 승인")
        self.assertEqual(tf.current_stage(st), 1)
        self.assertIn("✅ 11/01(일) 승인", (self.root / "TF.md").read_text(encoding="utf-8"))

    def test_drop_needs_reason_and_frees_the_gate(self):
        self.fill("TF.md")
        self.cli("task", "done", "T01")
        self.cli("task", "done", "T02")
        with self.assertRaises(SystemExit):
            self.cli("task", "drop", "T03")  # 이유 없음
        self.cli("task", "drop", "T03", "--why", "청중이 한 명이라 생략")
        self.cli("gate", "approve", "G0", "--quote", "승인")
        self.assertNotIn("T03", self.cli("brief", today="2026-11-05"))
        self.assertIn("취소 1", (self.root / "TF.md").read_text(encoding="utf-8"))

    def test_reject_needs_reason_and_rerequest_refreshes_memo(self):
        self.pass_gate(0)
        self.finish_stage(1)
        self.cli("gate", "request", "G1", today="2026-11-03")
        memo = self.root / "work" / "gates" / "G1.md"
        memo.write_text(memo.read_text(encoding="utf-8").replace("(작성: 추천", "파트너 추천: 진행. (작성: 추천"),
                        encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.cli("gate", "reject", "G1", "--quote", "다시")  # 이유 없음
        self.cli("gate", "reject", "G1", "--quote", "다시", "--note", "가설 근거 부족")
        self.assertEqual(self.state()["stages"][1]["gate"]["status"], "rejected")
        self.cli("raid", "add", "고객 자료가 늦다", "--level", "high")
        self.cli("gate", "request", "G1", today="2026-11-05")
        text = memo.read_text(encoding="utf-8")
        self.assertIn("파트너 추천: 진행.", text)  # 1~3절은 남는다
        self.assertIn("고객 자료가 늦다", text)  # 자동 기록은 새로
        self.assertIn("요청 11/05(목)", text)

    def test_memo_redteam_and_final_check_block_final_gate(self):
        self.pass_gate(0)
        with self.assertRaises(SystemExit):
            self.cli("gate", "approve", "G1", "--quote", "승인")  # 할 일·메모 없음
        self.finish_stage(1)
        self.cli("gate", "request", "G1")
        with self.assertRaises(SystemExit):
            self.cli("gate", "approve", "G1", "--quote", "승인")  # 메모 빈칸
        self.fill("work/gates/G1.md")
        self.cli("gate", "approve", "G1", "--quote", "승인")
        self.pass_gate(2)
        self.finish_stage(3)
        self.cli("gate", "request", "G3")
        self.fill("work/gates/G3.md")
        with self.assertRaises(SystemExit):
            self.cli("gate", "approve", "G3", "--quote", "승인")  # 최종본·레드팀 없음
        final = self.root / "work" / "final" / "report.md"
        final.write_text("# 보고서\n## 결론\n매출이 30% 늘었다.\n## 근거\n## 실행\n## 리스크\n", encoding="utf-8")
        self.cli("doc", "redteam")
        self.fill("work/redteam.md")
        with self.assertRaises(SystemExit):
            self.cli("gate", "approve", "G3", "--quote", "승인")  # 근거 없는 숫자
        with self.assertRaises(SystemExit):
            self.cli("gate", "approve", "G3", "--quote", "승인", "--force")  # 이유 없이 강행
        self.cli("source", "--title", "가상 판매 데이터", "--locator", "표1", "--status", "✅")
        final.write_text(final.read_text(encoding="utf-8").replace("늘었다.", "늘었다 [S1]."), encoding="utf-8")
        self.cli("gate", "approve", "G3", "--quote", "최종본 승인")
        self.assertEqual(tf.current_stage(self.state()), 4)

    def test_brief_shows_waiting_days_and_puts_decisions_first(self):
        self.cli("need", "add", "작년 거래처 명단", "--owner", "lead", "--why", "매출 집중 분석")
        self.fill("TF.md")
        self.cli("gate", "request", "G0", today="2026-11-02")
        out = self.cli("brief", today="2026-11-04")
        actions = out.split("지금 할 일:")[1].strip().splitlines()
        self.assertIn("G0 TF 헌장 승인 승인 여부 결정 (대표, 요청 2일째)", actions[0])
        self.assertIn("T01", actions[1])
        self.assertIn("N01 작년 거래처 명단(요청 3일째)", out)
        self.assertIn("관문 예정일이 2일 지났습니다", out)
        self.assertIn("늦어진 일 (3)", out)

    def test_brief_warns_on_late_stage_and_stale_board(self):
        self.pass_gate(0)
        out = self.cli("brief", today="2026-11-06")  # 진단 단계가 끝난 뒤
        self.assertIn("tf.py replan", out)
        self.assertIn("상태판이 5일째 갱신되지 않았습니다", out)

    def test_log_handover_tops_the_next_brief(self):
        self.cli("log", "헌장 초안 완료 / 대표: 성공 기준 확인 / 다음: 자료 요청 목록")
        out = self.cli("brief", today="2026-11-02").splitlines()
        self.assertEqual(out[1], "지난 세션 인계 (11/01(일)): 헌장 초안 완료 / 대표: 성공 기준 확인 / 다음: 자료 요청 목록")

    def test_replan_moves_remaining_stages_and_tasks(self):
        self.pass_gate(0)
        before = self.state()
        with self.assertRaises(SystemExit):
            self.cli("replan", "--deadline", "2026-11-20")  # 대표의 말 없음
        with self.assertRaises(SystemExit):
            self.cli("replan", "--deadline", "2026-02-30", "--quote", "미뤄요")  # 없는 날짜
        self.cli("replan", "--deadline", "2026-11-20", "--quote", "마감을 20일로 미뤄요",
                 "--why", "자료가 늦게 옴", today="2026-11-02")
        st = self.state()
        self.assertEqual(st["deadline"], "2026-11-20")
        self.assertEqual(st["stages"][0], before["stages"][0])  # 끝난 단계는 그대로
        self.assertEqual(st["stages"][1]["start"], before["stages"][1]["start"])  # 시작한 단계의 시작일도
        self.assertEqual(st["stages"][-1]["end"], "2026-11-20")
        ends = [s["end"] for s in st["stages"]]
        self.assertEqual(ends, sorted(ends))
        stage1 = [t for t in st["tasks"] if t["stage"] == 1]
        self.assertTrue(all(t["due"] == st["stages"][1]["end"] for t in stage1))
        self.assertIn("마감 변경 11/10(화) → 11/20(금)", st["decisions"][-1]["text"])

    def test_hypotheses_link_tasks(self):
        self.cli("hyp", "add", "재주문 지연 거래처가 이탈한다")
        self.cli("task", "add", "주문 간격 분석", "--hyp", "H1", "--stage", "2")
        with self.assertRaises(SystemExit):
            self.cli("task", "add", "없는 가설", "--hyp", "H9")
        self.assertIn("가설: H01 검증 중(할 일 0/1)", self.cli("brief"))
        self.cli("hyp", "set", "H1", "--status", "rejected", "--why", "계절성으로 설명됨")
        st = self.state()
        self.assertEqual(st["hyps"][0]["status"], "rejected")
        self.assertIn("H01 기각", st["decisions"][-1]["text"])
        with self.assertRaises(SystemExit):
            self.cli("hyp", "set", "H1", "--status", "maybe")

    def test_events_show_up_and_ask_for_results(self):
        self.cli("event", "add", "2026-11-12", "중간보고")
        self.cli("event", "add", "2026-12-30", "먼 일정")
        out = self.cli("brief", today="2026-11-05")
        self.assertIn("다가오는 일정 (14일 안): E01 11/12(목) 중간보고 (D-7)", out)
        self.assertNotIn("먼 일정", out)
        out = self.cli("brief", today="2026-11-13")
        self.assertIn("지난 일정, 결과 기록 필요: E01", out)
        self.cli("event", "done", "E01", "--why", "범위 승인")
        self.assertNotIn("E01", self.cli("brief", today="2026-11-13"))

    def test_doc_copies_templates_once(self):
        self.cli("doc", "redteam")
        self.assertTrue((self.root / "work" / "redteam.md").exists())
        with self.assertRaises(SystemExit):
            self.cli("doc", "redteam")
        self.cli("doc", "final_consulting")
        self.assertTrue((self.root / "work" / "final" / "report.md").exists())
        with self.assertRaises(SystemExit):
            self.cli("doc", "없는양식")

    def test_bad_input_gets_a_plain_message(self):
        for argv, words in ((("task", "add", "x", "--stage", "9"), "--stage는"),
                            (("task", "add", "x", "--due", "2026-13-01"), "--due 형식"),
                            (("event", "add", "내일", "회의"), "일정 날짜 형식")):
            with self.assertRaises(SystemExit) as e:
                self.cli(*argv)
            self.assertIn(words, str(e.exception))
        with self.assertRaises(SystemExit) as e:
            run("--dir", self.root, "--today", "어제", "brief")
        self.assertIn("--today 형식", str(e.exception))

    def test_records_and_close(self):
        self.cli("task", "add", "인터뷰 정리", "--owner", "lead", "--due", "2026-11-02")
        self.cli("task", "done", "T20")
        self.cli("raid", "add", "자료가 늦게 올 수 있음", "--kind", "risk", "--level", "high")
        self.cli("decide", "B2B부터 한다", "--why", "매출 비중", "--quote", "B2B 먼저")
        st = self.state()
        self.assertEqual(st["tasks"][-1]["status"], "done")
        self.assertEqual(st["raid"][0]["id"], "R01")
        self.assertEqual(st["decisions"][0]["text"], "B2B부터 한다")
        self.cli("close", today="2026-11-11")
        retro = (self.root / "work" / "retro.md").read_text(encoding="utf-8")
        self.assertIn("할 일: 완료 1/20, 취소 0", retro)
        self.assertEqual(self.state()["closed"], "2026-11-11")
        out = self.cli("brief", today="2026-11-12")
        self.assertIn("종료됐습니다", out)
        self.assertNotIn("늦어진 일", out)  # 종료 뒤에는 회고만 안내
        self.assertIn("회고 양식", out)

    def test_cli_runs_as_a_program(self):
        out = subprocess.run([sys.executable, str(self.root / "tf.py"), "--today", "2026-11-01", "brief"],
                             capture_output=True, text=True, encoding="utf-8", cwd=self.root)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("[수석 비서 브리핑]", out.stdout)
        late = subprocess.run([sys.executable, str(self.root / "tf.py"), "brief", "--today", "2026-11-04"],
                              capture_output=True, text=True, encoding="utf-8", cwd=self.root)
        self.assertIn("11/04(수)", late.stdout)  # 옵션을 명령 뒤에 써도 된다


class ResearchTest(unittest.TestCase):
    def test_last_gate_needs_an_upcoming_catalyst(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "r"
            run("--today", "2026-11-02", "new", "리서치", "--mode", "research", "--deadline", "2026-11-20",
                "--path", root)
            blockers = tf.gate_blockers(root, tf.load(root), 4, date(2026, 11, 20))
            self.assertTrue(any("다가오는 촉매 일정이 없습니다" in b for b in blockers))
            run("--dir", root, "--today", "2026-11-20", "event", "add", "2027-02-10", "4분기 실적")
            blockers = tf.gate_blockers(root, tf.load(root), 4, date(2026, 11, 20))
            self.assertFalse(any("다가오는 촉매 일정이 없습니다" in b for b in blockers))


class BenchTest(unittest.TestCase):
    def test_dev_set_is_fully_detected(self):
        rows = run_bench.run(ROOT / "bench" / "dev")
        tp, fn, fp, _ = run_bench.summarize(rows)
        self.assertEqual((fn, fp), (0, 0), [(r["file"], r["fn"], r["fp"]) for r in rows if r["fn"] or r["fp"]])
        self.assertGreaterEqual(tp, 25)

    def test_blind_sets_still_pass(self):
        for name in ("heldout_v1", "heldout_v2"):
            rows = run_bench.run(ROOT / "bench" / name)
            tp, fn, fp, _ = run_bench.summarize(rows)
            self.assertEqual((fn, fp), (0, 0), (name, [(r["file"], r["fn"], r["fp"]) for r in rows if r["fn"] or r["fp"]]))


if __name__ == "__main__":
    unittest.main()
