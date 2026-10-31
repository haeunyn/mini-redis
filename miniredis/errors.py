"""에러 메시지 표준 — 과제 명세의 출력 형식을 한곳에 모아둔다.

한곳에 모으는 이유: 명령어마다 문자열을 흩어 적으면 오타가 나고,
명세가 바뀌었을 때 고칠 곳을 찾아다녀야 한다.
"""


class MiniRedisError(Exception):
    """CLI 가 '(error) ...' 형태로 출력하는 모든 오류의 부모."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnknownCommandError(MiniRedisError):
    def __init__(self, cmd: str) -> None:
        super().__init__(f"ERR unknown command '{cmd}'")


class WrongArityError(MiniRedisError):
    def __init__(self, cmd: str) -> None:
        super().__init__(f"ERR wrong number of arguments for '{cmd}' command")


class NotAnIntegerError(MiniRedisError):
    def __init__(self) -> None:
        super().__init__("ERR value is not an integer or out of range")


class OutOfMemoryError(MiniRedisError):
    def __init__(self) -> None:
        super().__init__(
            "OOM command not allowed when used_memory > 'maxmemory'"
        )
