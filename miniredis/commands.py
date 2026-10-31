"""명령어 실행기 — 토큰을 받아 Store 를 호출하고 Redis 스타일 문자열을 돌려준다.

출력 형식을 이 파일 한 곳에 모아두면, CLI 는 '읽고-넘기고-찍기'만 하면 된다.
덕분에 테스트도 CLI 없이 이 함수만 호출해서 할 수 있다.
"""

from .errors import (
    MiniRedisError,
    NotAnIntegerError,
    UnknownCommandError,
    WrongArityError,
)
from .parser import parse_int, tokenize
from .pubsub import PubSub, Subscriber
from .store import Store

OK = "OK"
NIL = "(nil)"
EMPTY_ARRAY = "(empty array)"


def integer(n: int) -> str:
    return f"(integer) {n}"


class CommandExecutor:
    """한 줄 입력 → 한 덩어리 출력."""

    def __init__(self, store: Store = None) -> None:
        self.store = store if store is not None else Store()
        # 보너스 5: Pub/Sub. CLI 세션 자체가 하나의 구독자다.
        self.pubsub = PubSub()
        self.session = Subscriber("cli")

    def execute_line(self, line: str) -> str:
        """CLI 가 호출하는 진입점. 오류도 문자열로 바꿔 돌려준다."""
        tokens = tokenize(line)
        if not tokens:
            return ""
        try:
            output = self.execute(tokens)
        except MiniRedisError as exc:
            return f"(error) {exc.message}"
        # 발행된 메시지가 수신함에 있으면 이어서 보여준다
        delivered = self.session.inbox.drain()
        for channel, message in delivered:
            output += f'\n1. "message"\n2. "{channel}"\n3. "{message}"'
        return output

    def execute(self, tokens) -> str:
        cmd = tokens[0].upper()
        args = tokens[1:]

        if cmd == "SET":
            return self._set(args)
        if cmd == "GET":
            return self._get(args)
        if cmd == "DEL":
            return self._del(args)
        if cmd == "EXISTS":
            return self._exists(args)
        if cmd == "DBSIZE":
            return self._dbsize(args)
        if cmd == "KEYS":
            return self._keys(args)
        if cmd == "EXPIRE":
            return self._expire(args)
        if cmd == "TTL":
            return self._ttl(args)
        if cmd == "CONFIG":
            return self._config(args)
        if cmd == "INFO":
            return self._info(args)
        if cmd == "SUBSCRIBE":
            return self._subscribe(args)
        if cmd == "UNSUBSCRIBE":
            return self._unsubscribe(args)
        if cmd == "PUBLISH":
            return self._publish(args)
        raise UnknownCommandError(tokens[0])

    # ---- String 기본 명령어 (6개) ----
    def _set(self, args) -> str:
        if len(args) != 2:
            raise WrongArityError("SET")
        self.store.set(args[0], args[1])  # 한도 초과 시 내부에서 OOM 발생
        return OK

    def _get(self, args) -> str:
        if len(args) != 1:
            raise WrongArityError("GET")
        value = self.store.get(args[0])
        return NIL if value is None else f'"{value}"'

    def _del(self, args) -> str:
        if len(args) != 1:
            raise WrongArityError("DEL")
        return integer(1 if self.store.delete(args[0]) else 0)

    def _exists(self, args) -> str:
        if len(args) != 1:
            raise WrongArityError("EXISTS")
        return integer(1 if self.store.exists(args[0]) else 0)

    def _dbsize(self, args) -> str:
        if args:
            raise WrongArityError("DBSIZE")
        return integer(self.store.dbsize())

    def _keys(self, args) -> str:
        if args:
            raise WrongArityError("KEYS")
        keys = self.store.keys()
        if not keys:
            return EMPTY_ARRAY
        return "\n".join(f'{i}. "{k}"' for i, k in enumerate(keys, 1))

    # ---- TTL 관리 (2개) ----
    def _expire(self, args) -> str:
        if len(args) != 2:
            raise WrongArityError("EXPIRE")
        try:
            seconds = parse_int(args[1])
        except ValueError:
            raise NotAnIntegerError()
        return integer(1 if self.store.expire(args[0], seconds) else 0)

    def _ttl(self, args) -> str:
        if len(args) != 1:
            raise WrongArityError("TTL")
        return integer(self.store.ttl(args[0]))

    # ---- 메모리 관리 (2개) ----
    def _config(self, args) -> str:
        # CONFIG SET maxmemory <bytes>
        if len(args) != 3 or args[0].upper() != "SET" or args[1].lower() != "maxmemory":
            raise WrongArityError("CONFIG")
        try:
            value = parse_int(args[2])
        except ValueError:
            raise NotAnIntegerError()
        if value < 0:
            raise NotAnIntegerError()
        self.store.config_set_maxmemory(value)
        return OK

    def _info(self, args) -> str:
        # INFO memory
        if len(args) != 1 or args[0].lower() != "memory":
            raise WrongArityError("INFO")
        used, maxmem, evicted = self.store.info_memory()
        return f"used_memory:{used}\nmaxmemory:{maxmem}\nevicted_keys:{evicted}"

    # ---- 보너스 5: Pub/Sub ----
    def _subscribe(self, args) -> str:
        if len(args) != 1:
            raise WrongArityError("SUBSCRIBE")
        count = self.pubsub.subscribe(args[0], self.session)
        return f'1. "subscribe"\n2. "{args[0]}"\n3. {integer(count)}'

    def _unsubscribe(self, args) -> str:
        if len(args) != 1:
            raise WrongArityError("UNSUBSCRIBE")
        self.pubsub.unsubscribe(args[0], self.session)
        count = self.pubsub.subscription_count(self.session)
        return f'1. "unsubscribe"\n2. "{args[0]}"\n3. {integer(count)}'

    def _publish(self, args) -> str:
        if len(args) != 2:
            raise WrongArityError("PUBLISH")
        return integer(self.pubsub.publish(args[0], args[1]))
