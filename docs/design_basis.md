# 설계 근거

이 청사진의 규칙이 어디서 왔는지 적는다. 확인 수준: ✅ 2026-11-01에 원문(공식 PDF·웹)을 직접 열어 해당 내용을 확인 · ⚠️ 자료 수집(Gemini, Antigravity CLI) 결과에만 있고 원문은 못 열어 봄.
원문을 확인하지 못한 자료는 규칙의 "영감"으로만 쓰고, 프로그램이 강제하는 규칙의 유일한 근거로 쓰지 않았다.

## 1. 정확도 체계 (`tf.py check`, common.md §4)

| 설계 요소 | 근거 | 출처 | 확인 |
|---|---|---|---|
| 사실·가정·판단을 구분하는 표시 `[S번호]` `[가정]` `[계산]` `[추정]` | 분석 결과물은 근거 정보와 분석가의 가정·판단을 분명히 구분해야 한다(표준 3), 근거 출처와 방법의 품질을 설명해야 한다(표준 1) | ODNI, *ICD 203: Analytic Standards*, 2015-01-02, https://www.dni.gov/files/documents/ICD/ICD-203.pdf | ✅ |
| 확률 표현 7단계 척도 (거의 없음 1–5% … 거의 확실 95–99%)와 HEDGE 경고 | 불확실성을 표현하고 설명해야 하며(표준 2), 확률 표현은 7단계 용어와 구간(01–05, 05–20, 20–45, 45–55, 55–80, 80–95, 95–99%)을 쓴다 | 위와 같음 | ✅ |
| 출처 확인 수준 ✅/⚠️/❓, 최종본에 ❓ 출처 금지, 목록에 없는 출처 번호 금지 | 투자 분석에는 적절한 조사에 바탕을 둔 합리적이고 충분한 근거가 있어야 한다 | CFA Institute, *Standard V(A) Diligence and Reasonable Basis*, https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-v-a | ✅ |
| 모르면 모른다고 쓰고 출처를 지어내지 않는다 | 언어 모델의 환각이 남는 이유 중 하나는 평가가 불확실성 인정보다 추측에 보상하기 때문이다 | Kalai 외, *Why Language Models Hallucinate*, arXiv:2509.04664, 2025-09-04, https://arxiv.org/abs/2509.04664 | ✅ |
| 기록 보관(모델 입력값, 원문 위치, 결정 이유) | 분석·추천·행동을 뒷받침하는 기록을 만들고 유지해야 한다 | CFA Institute, *Standard V(C) Record Retention*, https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-v-c | ✅ |

## 2. 관문과 체크리스트

| 설계 요소 | 근거 | 출처 | 확인 |
|---|---|---|---|
| 단계 끝마다 관문, 관문마다 짧은 통과 기준 목록 | 정해진 멈춤 지점에서 짧은 체크리스트를 쓰자 수술 사망률이 1.5%에서 0.8%로, 주요 합병증이 11.0%에서 7.0%로 줄었다(8개 도시 병원, 전후 비교). 분야가 다르므로 "멈춤 지점 + 짧은 목록"이라는 형식만 빌렸다 | Haynes 외, *A Surgical Safety Checklist to Reduce Morbidity and Mortality in a Global Population*, NEJM 2009, https://pubmed.ncbi.nlm.nih.gov/19144931/ | ✅ |
| 관문 승인은 대표의 말(`--quote`)이 있어야 기록, 순서 위반·헌장 빈칸·최종본 점검 오류는 프로그램이 막음 | 단계 게이트(진행·보류·중단 결정)와 결정 기록은 프로젝트 관리 표준 도구다 | European Commission, *PM² Project Management Methodology Guide 3.0.1*, 2021 | ⚠️ |
| 리서치 방식의 '발간 심의' 관문 | 미국에서는 리서치 보고서의 공표 전 검토를 투자은행 인력이 하지 못하게 하고, 분석 대상 기업에 사실 확인용 초안을 보낼 때도 요약·투자의견·목표주가를 빼고 법무·컴플라이언스가 먼저 전체 초안을 받는다 → 심의는 작성과 분리된 관점에서 한다 | FINRA, *Rule 2241 Research Analysts and Research Reports*, https://www.finra.org/rules-guidance/rulebooks/finra-rules/2241 | ✅ |

## 3. 파트너의 도구

| 설계 요소 | 근거 | 출처 | 확인 |
|---|---|---|---|
| 핵심 가정 점검, 악마의 변호인, 레드팀 | 구조화 분석 기법을 진단(핵심 가정 점검, 경쟁가설분석 등)·반론(악마의 변호인 등)·상상(레드팀 분석 등) 기법으로 정리 | US Government, *A Tradecraft Primer: Structured Analytic Techniques for Improving Intelligence Analysis*, 2009-03, https://www.cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf | ✅ |
| 대안 분석을 최종본 전에 반드시 | 분석 결과물은 대안 분석을 포함해야 한다(표준 4) | ICD 203 (위) | ✅ |
| 사전 부검 | 프로젝트가 이미 실패했다고 가정하고 그럴듯한 실패 이유를 먼저 적는다 | Klein, *Performing a Project Premortem*, Harvard Business Review, 2007-09, https://hbr.org/2007/09/performing-a-project-premortem | ✅ |
| 헌장 항목(핵심 질문·배경·성공 기준·범위·제약·이해관계자·자료원) | 문제 정의 워크시트의 구성 | Conn·McLean, *Bulletproof Problem Solving*, Wiley, 2019 (도서) | ⚠️ |
| 고스트 덱·답 먼저 | 데이터를 다 모으기 전에 결론 문장형 헤드라인으로 골격을 먼저 짠다 | 컨설팅 실무 해설(Slideworks 등) | ⚠️ |
| 레드팀 리뷰를 최종본 직전에, 평가자의 눈으로 | 제안서 품질관리의 컬러팀 리뷰 | Shipley Associates 용어집 | ⚠️ |

## 4. 수석 비서의 역할과 회고

| 설계 요소 | 근거 | 출처 | 확인 |
|---|---|---|---|
| 수석 비서(Chief of Staff)라는 역할 설정 | 리더에게는 비서 이상의 지원이 필요하다는 문제 제기 (제목·요약만 확인. 세부 책임 목록은 원문 미확인) | Ciampa, *The Case for a Chief of Staff*, Harvard Business Review, 2020 5–6월호, https://hbr.org/2020/05/the-case-for-a-chief-of-staff | ✅(제목·요지) |
| 정보 흐름·의제·후속조치·직언 | 비서실장 역할 유형(관리·통합, 게이트키퍼, 조언자, 실행가, 대리인) | McKinsey, *Chief of staff: Anatomy of the role in eight charts*, 2024 (페이지 응답 없음) | ⚠️ |
| 회고 네 질문 | 무엇을 하려 했나 / 실제로 무슨 일이 있었나 / 왜 / 무엇을 유지·개선하나 | US Army, *TC 25-20 A Leader's Guide to After-Action Reviews*, 1993 (PDF 인증서 오류로 못 엶) | ⚠️ |
| 리서치 최종본 필수 절 | 기업 분석 보고서의 표준 구성(사업 설명, 산업·경쟁, 투자 요약, 가치평가, 재무 분석, 리스크) | CFA Institute, *Equity Research Report Essentials* | ⚠️ |

## 5. 작성자의 기존 작업 방식

상태판, 관문 승인, 결정 기록, ✅/⚠️ 출처 표시, 고스트 덱, 레드팀 3관점은 작성자가 2026년 10월 공모전 지원서를 준비하며 AI와 함께 쓰던 운영 문서에서 가져와 일반화했다.

## 6. v2 개정(실무자 관점 검토)의 근거

v2의 16개 변경은 AI가 컨설팅·리서치·PMO·사실 확인 실무자의 눈으로 이 틀을 직접 돌려 보며 찾은 문제에서 나왔다(예: 할 일 0개로 관문 5개가 통과됨, 세션 인계를 둘 곳이 없음). 아래 근거는 대부분 실무 관행 해설이라 ⚠️다.

| 설계 요소 | 근거 | 확인 |
|---|---|---|
| 고스트 덱을 분석 전에 먼저 그림 | 데이터를 다 모으기 전에 헤드라인으로 골격을 짜고 필요한 분석을 역산한다(위 §3 고스트 덱과 같은 해설) | ⚠️ |
| 할 일을 가설에 연결 | 가설 주도 워크플랜: 가설 가지마다 검증 분석·자료·담당·마감을 연결한다(컨설팅 실무 해설) | ⚠️ |
| 마감 재배분과 결정 기록, 할 일 취소 사유 | 범위·일정 변경을 공식 결정으로 남기는 변경 관리(PM² 등 프로젝트 관리 지침) | ⚠️ |
| 세션 인계, 대기 일수 표시 | 비서실장의 정보 흐름·후속조치 추적 역할(위 §4) | ⚠️ |
| 계산·추정의 근거 파일, 출처의 쪽·표 위치와 확인일 | 분석을 뒷받침하는 기록을 남겨야 한다(CFA Standard V(C), 위 §1) | ✅ |
| 리서치 최종본의 컨센서스 대비 절 | 논지가 시장 기대와 어디서 다른지 보여야 한다(시장과 다른 관점, 수집 자료) | ⚠️ |
| 미공개 중요정보를 쓰지 않는 규칙 | 리서치 실무의 기본 규칙으로 넣었다. 이번에 원문 규정을 확인하지는 않았다 | 미확인 |

## 7. 확인하지 못해 쓰지 않은 것

- 한국 금융투자협회 조사분석자료 심의 규정(조항 번호, 괴리율 공시 등): 협회 법규 사이트가 자동 접속을 막아 원문을 못 봤다. 리서치 방식의 규칙에 넣지 않았다.
- 사전 부검이 원인 식별을 30% 높인다는 수치(Mitchell 외 1989 연구로 알려짐): 원문을 확인하지 못해 쓰지 않았다.
