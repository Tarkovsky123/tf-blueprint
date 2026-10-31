# 결함 심기 시험 결과

`python bench/run_bench.py`가 만든다. 정답 표시와 `tf.py check` 결과를 줄 단위로 대조한다.

## dev

문서 8개 · 정답 결함 28개 · 맞게 잡음 28 · 놓침 0 · 잘못 잡음 0
정밀도 100.0% · 재현율 100.0%

| 코드 | 맞게 잡음 | 놓침 | 잘못 잡음 |
|---|---|---|---|
| ANSWER_NOT_FIRST | 1 | 0 | 0 |
| CALC_NOFILE | 1 | 0 | 0 |
| HEDGE | 3 | 0 | 0 |
| NUM_NOSRC | 11 | 0 | 0 |
| PLACEHOLDER | 3 | 0 | 0 |
| SECTION_MISSING | 4 | 0 | 0 |
| SRC_NOLOCATOR | 1 | 0 | 0 |
| SRC_UNKNOWN | 2 | 0 | 0 |
| SRC_UNVERIFIED | 2 | 0 | 0 |

## heldout_v1

문서 10개 · 정답 결함 51개 · 맞게 잡음 51 · 놓침 0 · 잘못 잡음 0
정밀도 100.0% · 재현율 100.0%

| 코드 | 맞게 잡음 | 놓침 | 잘못 잡음 |
|---|---|---|---|
| ANSWER_NOT_FIRST | 2 | 0 | 0 |
| CALC_NOFILE | 18 | 0 | 0 |
| HEDGE | 3 | 0 | 0 |
| NUM_NOSRC | 7 | 0 | 0 |
| PLACEHOLDER | 4 | 0 | 0 |
| SECTION_MISSING | 6 | 0 | 0 |
| SRC_UNKNOWN | 6 | 0 | 0 |
| SRC_UNVERIFIED | 5 | 0 | 0 |

## heldout_v2

문서 10개 · 정답 결함 36개 · 맞게 잡음 36 · 놓침 0 · 잘못 잡음 0
정밀도 100.0% · 재현율 100.0%

| 코드 | 맞게 잡음 | 놓침 | 잘못 잡음 |
|---|---|---|---|
| ANSWER_NOT_FIRST | 2 | 0 | 0 |
| CALC_NOFILE | 4 | 0 | 0 |
| HEDGE | 4 | 0 | 0 |
| NUM_NOSRC | 9 | 0 | 0 |
| PLACEHOLDER | 2 | 0 | 0 |
| SECTION_MISSING | 4 | 0 | 0 |
| SRC_NOLOCATOR | 2 | 0 | 0 |
| SRC_UNKNOWN | 5 | 0 | 0 |
| SRC_UNVERIFIED | 4 | 0 | 0 |
