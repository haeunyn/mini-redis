"""REPL — 입력을 읽고(Read), 실행하고(Eval), 찍고(Print), 반복(Loop)."""

import sys

from .commands import CommandExecutor

PROMPT = "mini-redis> "
BANNER = (
    "Mini Redis — 해시맵/이중연결리스트/힙을 직접 구현한 인메모리 저장소\n"
    "명령어: SET GET DEL EXISTS DBSIZE KEYS EXPIRE TTL "
    "CONFIG SET maxmemory / INFO memory\n"
    "종료: exit 또는 quit\n"
)


def run(stdin=None, show_banner: bool = True) -> int:
    """REPL 을 돈다.

    stdin 을 주입받는 이유: 데모 스크립트(demo/*.txt)를 파이프로 흘려넣어
    같은 코드로 자동 시연을 할 수 있게 하기 위해서다.
    """
    stream = stdin if stdin is not None else sys.stdin
    executor = CommandExecutor()
    interactive = stream is sys.stdin and sys.stdin.isatty()

    if show_banner and interactive:
        print(BANNER)

    while True:
        if interactive:
            try:
                line = input(PROMPT)
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
        else:
            line = stream.readline()
            if not line:
                return 0
            line = line.rstrip("\n")
            # 파이프 입력일 때는 무엇을 입력했는지 같이 보여줘야 읽을 수 있다
            print(f"{PROMPT}{line}")

        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):  # 데모 스크립트의 주석
            if interactive:           # 파이프 입력일 땐 위에서 이미 찍었다
                print(stripped)
            continue
        if stripped.lower() in ("exit", "quit"):
            return 0

        output = executor.execute_line(stripped)
        if output:
            print(output)
