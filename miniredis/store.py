"""Mini Redis 저장소 엔진 — 해시맵 + 이중 연결 리스트 + 힙을 조립한 곳.

세 자료구조가 각자 맡은 일:
    HashMap           키 → Entry 를 평균 O(1) 로 찾는다
    DoublyLinkedList  '최근 쓴 순서' 줄. 맨 앞=방금 쓴 것, 맨 뒤=가장 오래된 것
    MinHeap           '가장 먼저 만료될 키'를 O(1) 로 들여다본다

LRU 가 O(1) 인 이유(평가에서 반드시 나오는 질문):
    해시맵만 있으면 "가장 오래된 키"를 찾으려고 전부 훑어야 한다 → O(n).
    연결 리스트만 있으면 특정 키의 위치를 찾으려고 훑어야 한다 → O(n).
    둘을 합치고, Entry 가 자기 LRU 노드를 가리키게 하면
    "키로 노드를 즉시 찾아(해시맵) 그 노드를 즉시 맨 앞으로 옮긴다(리스트)"
    가 되어 양쪽 다 O(1) 이 된다. 이 포인터 하나가 핵심이다.
"""

import time

from .errors import OutOfMemoryError
from .hash_map import HashMap
from .heap import MinHeap
from .linked_list import DoublyLinkedList


def _utf8_len(text: str) -> int:
    """UTF-8 로 인코딩했을 때의 바이트 수.

    한글은 글자당 3바이트라 len(문자열) 과 다르다.
    과제의 used_memory 공식이 utf8 기준이므로 여기에 맞춘다.
    """
    return len(text.encode("utf-8"))


class Entry:
    """키 하나에 대한 모든 정보를 담는 상자."""

    __slots__ = ("key", "value", "lru_node", "expire_at")

    def __init__(self, key: str, value: str) -> None:
        self.key = key
        self.value = value
        self.lru_node = None   # LRU 줄에서 이 키가 서 있는 자리(O(1) 이동의 비결)
        self.expire_at = None  # 만료 시각(epoch 초). None 이면 만료 없음

    def size(self) -> int:
        """이 항목이 차지하는 것으로 '계산하는' 바이트 수."""
        return _utf8_len(self.key) + _utf8_len(self.value)


class Store:
    """Mini Redis 의 데이터 저장소."""

    def __init__(self, clock=time.time) -> None:
        # clock 을 주입받는 이유: 테스트에서 시간을 마음대로 돌려
        # TTL 만료를 기다리지 않고 검증하기 위해서다.
        self._clock = clock
        self._map = HashMap()          # key -> Entry
        self._lru = DoublyLinkedList() # 최근 쓴 순서 (앞=최신)
        self._ttl_heap = MinHeap()     # (expire_at, key)
        self.used_memory = 0
        self.maxmemory = 0             # 0 = 무제한
        self.evicted_keys = 0

    # ================= 내부 도우미 =================
    def _now(self) -> float:
        return self._clock()

    def _is_expired(self, entry: Entry) -> bool:
        return entry.expire_at is not None and entry.expire_at <= self._now()

    def _drop(self, entry: Entry) -> None:
        """엔트리를 모든 구조에서 완전히 제거한다.

        데이터/LRU/TTL 세 군데에 흔적이 남으므로 전부 지워야 한다.
        (TTL 힙에 남은 항목은 즉시 지우지 않고 '게으른 삭제'로 처리한다 — 아래 설명)
        """
        self._map.remove(entry.key)
        if entry.lru_node is not None:
            self._lru.remove_node(entry.lru_node)
            entry.lru_node = None
        self.used_memory -= entry.size()

    def _lookup(self, key: str):
        """살아 있는 엔트리를 찾는다. 만료됐으면 지우고 None 을 돌려준다.

        모든 키 기반 명령어가 여기를 먼저 거친다(명세의 '만료 여부 선확인').
        """
        entry = self._map.get(key)
        if entry is None:
            return None
        if self._is_expired(entry):
            self._drop(entry)
            return None
        return entry

    def purge_expired(self) -> int:
        """힙을 이용해 만료된 키를 한꺼번에 치운다. 치운 개수를 돌려준다.

        힙이 빛나는 지점: 맨 위만 보면 '가장 이른 만료'를 O(1) 로 알 수 있으므로,
        아직 만료되지 않았으면 거기서 멈추면 된다. 전체를 훑을 필요가 없다.

        게으른 삭제(lazy deletion):
            EXPIRE 를 다시 걸거나 키를 지워도 힙에 든 옛 항목은 그대로 남는다.
            힙 중간에서 특정 항목을 찾아 빼는 건 O(n) 이라 비싸기 때문이다.
            대신 꺼낼 때 '지금 엔트리와 만료 시각이 일치하는가'를 확인해서
            어긋나면 버린다. 이쪽이 훨씬 싸다.
        """
        now = self._now()
        removed = 0
        while not self._ttl_heap.is_empty():
            expire_at, key = self._ttl_heap.peek()
            if expire_at > now:
                break  # 맨 위가 아직 안 끝났으면 나머지는 볼 것도 없다
            self._ttl_heap.pop()
            entry = self._map.get(key)
            # 유효성 확인: 이미 지워졌거나 TTL 이 바뀐 '유령 항목'이면 무시
            if entry is not None and entry.expire_at == expire_at:
                self._drop(entry)
                removed += 1
        return removed

    def _touch(self, entry: Entry) -> None:
        """'방금 이 키를 썼다'고 표시한다 — LRU 줄 맨 앞으로. O(1)."""
        if entry.lru_node is None:
            entry.lru_node = self._lru.insert_front(entry.key)
        else:
            self._lru.move_to_front(entry.lru_node)

    def _evict_until_fit(self) -> None:
        """메모리 한도 안에 들어올 때까지 가장 오래된 키부터 제거한다."""
        while (
            self.maxmemory > 0
            and self.used_memory > self.maxmemory
            and not self._lru.is_empty()
        ):
            victim_key = self._lru.back()  # 맨 뒤 = 가장 오래 안 쓴 키
            victim = self._map.get(victim_key)
            if victim is None:  # 방어: 어긋난 경우 줄에서만 떼어낸다
                self._lru.remove_back()
                continue
            self._drop(victim)
            self.evicted_keys += 1

    # ================= 명령 구현 =================
    def set(self, key: str, value: str) -> None:
        """SET. 메모리 초과 시 LRU 제거를 수행한다."""
        incoming = _utf8_len(key) + _utf8_len(value)

        # 단일 항목 자체가 한도를 넘으면 저장하지 않고 OOM
        if self.maxmemory > 0 and incoming > self.maxmemory:
            raise OutOfMemoryError()

        old = self._map.get(key)
        if old is not None:
            # 덮어쓰기: 기존 크기를 빼고, 명세대로 기존 TTL 을 초기화한다
            self.used_memory -= old.size()
            old.value = value
            old.expire_at = None
            entry = old
        else:
            entry = Entry(key, value)
            self._map.put(key, entry)

        self.used_memory += entry.size()
        self._touch(entry)       # 방금 썼으므로 맨 앞으로
        self._evict_until_fit()  # 한도를 넘었으면 오래된 것부터 정리

    def get(self, key: str):
        """GET. 값이 없거나 만료면 None. 성공했을 때만 LRU 를 갱신한다."""
        entry = self._lookup(key)
        if entry is None:
            return None
        self._touch(entry)
        return entry.value

    def delete(self, key: str) -> bool:
        entry = self._lookup(key)
        if entry is None:
            return False
        self._drop(entry)
        return True

    def exists(self, key: str) -> bool:
        return self._lookup(key) is not None

    def dbsize(self) -> int:
        self.purge_expired()
        return self._map.size()

    def keys(self):
        """살아 있는 키 전체를 파이썬 리스트로 돌려준다(출력 전용)."""
        self.purge_expired()
        arr = self._map.keys()
        return [arr[i] for i in range(len(arr))]

    def expire(self, key: str, seconds: int) -> bool:
        """EXPIRE. 키가 없으면 False. 0 이하면 즉시 만료(삭제) 후 True."""
        entry = self._lookup(key)
        if entry is None:
            return False
        if seconds <= 0:
            self._drop(entry)
            return True
        entry.expire_at = self._now() + seconds
        self._ttl_heap.push((entry.expire_at, key))
        return True

    def ttl(self, key: str) -> int:
        """TTL. 없으면 -2, 만료 설정이 없으면 -1, 있으면 남은 초."""
        entry = self._lookup(key)
        if entry is None:
            return -2
        if entry.expire_at is None:
            return -1
        return int(entry.expire_at - self._now())

    def config_set_maxmemory(self, value: int) -> None:
        self.maxmemory = value
        self._evict_until_fit()  # 한도를 줄였다면 즉시 반영

    def info_memory(self):
        self.purge_expired()
        return (self.used_memory, self.maxmemory, self.evicted_keys)
