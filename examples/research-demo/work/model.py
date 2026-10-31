"""가상소재 추정 모델 (예시용 가상 숫자). 실행: python work/model.py"""
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
