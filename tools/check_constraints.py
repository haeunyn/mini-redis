"""제약 사항 자동 검사기.

과제 제약: dict / set / collections 를 쓰지 않는다.

grep 으로는 정확히 검사할 수 없다. 예를 들어 `self.store.set(...)` 은
내가 만든 메서드 호출이지 내장 set() 이 아닌데, 단순 문자열 검색은 이걸
구분하지 못한다. 그래서 파이썬의 ast 모듈로 **구문 트리를 직접 읽어**
"진짜 내장 dict/set 을 쓴 곳"만 찾아낸다.

사용법:  python3 tools/check_constraints.py
"""

import ast
import pathlib
import sys

TARGET_DIR = pathlib.Path(__file__).resolve().parent.parent / "miniredis"
BANNED_NAMES = ("dict", "set", "frozenset")
BANNED_MODULES = ("collections",)


class ConstraintVisitor(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations = []

    def _report(self, node, message: str) -> None:
        self.violations.append((self.filename, node.lineno, message))

    def visit_Import(self, node):
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in BANNED_MODULES:
                self._report(node, f"import {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module.split(".")[0] in BANNED_MODULES:
            self._report(node, f"from {node.module} import ...")
        self.generic_visit(node)

    def visit_Name(self, node):
        # 이름이 그대로 쓰인 경우만 잡는다.
        # obj.set(...) 은 Attribute 노드라서 여기 걸리지 않는다 — 이게 핵심.
        if isinstance(node.ctx, ast.Load) and node.id in BANNED_NAMES:
            self._report(node, f"내장 {node.id} 사용")
        self.generic_visit(node)

    def visit_Dict(self, node):
        self._report(node, "딕셔너리 리터럴 {...}")
        self.generic_visit(node)

    def visit_Set(self, node):
        self._report(node, "집합 리터럴 {...}")
        self.generic_visit(node)

    def visit_DictComp(self, node):
        self._report(node, "딕셔너리 컴프리헨션")
        self.generic_visit(node)

    def visit_SetComp(self, node):
        self._report(node, "집합 컴프리헨션")
        self.generic_visit(node)


def main() -> int:
    all_violations = []
    files = sorted(TARGET_DIR.glob("*.py"))

    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = ConstraintVisitor(path.name)
        visitor.visit(tree)
        all_violations.extend(visitor.violations)

    print(f"검사 대상: miniredis/ 의 파이썬 파일 {len(files)}개")
    print("금지 항목: dict, set, frozenset, collections, {} 리터럴/컴프리헨션")
    print("-" * 56)

    if all_violations:
        for filename, lineno, message in all_violations:
            print(f"  ✗ {filename}:{lineno}  {message}")
        print("-" * 56)
        print(f"위반 {len(all_violations)}건 — 제약을 지키지 못했습니다.")
        return 1

    print("  위반 없음")
    print("-" * 56)
    print("✅ dict / set / collections 를 전혀 사용하지 않았습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
