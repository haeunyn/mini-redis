#!/usr/bin/env bash
# Mini Redis 실행 도우미
#   ./run.sh         대화형 REPL 실행
#   ./run.sh demo    데모 스크립트 자동 실행
#   ./run.sh test    테스트 전체 실행
#   ./run.sh check   제약 사항(dict/set/collections 미사용) 검사
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3}

case "${1:-repl}" in
  repl) exec "$PY" -m miniredis ;;
  demo) "$PY" -m miniredis < demo/demo.txt ;;
  test) "$PY" -m unittest discover -s tests -t . -v ;;
  check) "$PY" -I tools/check_constraints.py ;;
  *)    echo "사용법: ./run.sh [repl|demo|test|check]" >&2; exit 1 ;;
esac
