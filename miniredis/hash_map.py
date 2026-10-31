"""해시맵 — 체이닝 방식으로 직접 구현.

파이썬 dict 를 쓰면 한 줄이지만, 이 미션의 목적은 "dict 안에서 무슨 일이
일어나는가"를 손으로 확인하는 것이다. 그래서 dict/set/collections 를 쓰지 않는다.

큰 그림:
    키를 숫자(해시값)로 바꾼다 → 그 숫자로 버킷 번호를 고른다 → 그 버킷에 넣는다.
    서로 다른 키가 같은 버킷을 고르는 일(충돌)이 반드시 생기는데,
    버킷마다 연결 리스트를 달아 거기에 줄줄이 매단다. 이게 '체이닝'이다.
"""

from .dynamic_array import DynamicArray
from .linked_list import DoublyLinkedList

# 로드 팩터: 저장된 항목 수 / 버킷 수.
# 0.75 를 넘으면 버킷을 2배로 늘린다. 왜 0.75 인가?
#   너무 낮으면 → 빈 버킷이 많아 메모리 낭비
#   너무 높으면 → 한 버킷에 여러 개가 쌓여 탐색이 O(1) 에서 멀어짐
# 0.75 는 두 손해가 균형을 이루는 지점으로 널리 쓰이는 값이다(자바 HashMap 등).
MAX_LOAD_FACTOR = 0.75


class _Pair:
    """버킷 안에 저장되는 (키, 값) 한 쌍."""

    __slots__ = ("key", "value")

    def __init__(self, key, value) -> None:
        self.key = key
        self.value = value

    def __repr__(self) -> str:
        return f"{self.key!r}: {self.value!r}"


class HashMap:
    """체이닝 해시맵. put/get/remove/contains/keys/size 평균 O(1)."""

    def __init__(self, initial_buckets: int = 8) -> None:
        self._buckets = DynamicArray(initial_buckets)
        for _ in range(initial_buckets):
            self._buckets.append(DoublyLinkedList())
        self._size = 0

    # ---- 해시 함수 (직접 설계) ----
    @staticmethod
    def _hash(key) -> int:
        """FNV-1a 방식의 문자열 해시.

        동작: 시작값에서 출발해 글자 하나마다
              (1) XOR 로 섞고 (2) 소수를 곱해 흩뜨린다.
        왜 이렇게 하나:
            글자를 단순히 더하면 "abc" 와 "cba" 가 같은 값이 되어 충돌이 쏟아진다.
            곱셈은 앞 글자의 영향을 위쪽 비트까지 퍼뜨려서, 한 글자만 달라도
            결과가 확 달라지게 만든다.
        """
        FNV_OFFSET = 0x811C9DC5  # 시작값 (FNV 규격이 정한 상수)
        FNV_PRIME = 0x01000193   # 곱할 소수
        MASK32 = 0xFFFFFFFF      # 32비트로 잘라 값이 무한정 커지지 않게 한다

        h = FNV_OFFSET
        for byte in str(key).encode("utf-8"):
            h ^= byte                  # (1) 섞기
            h = (h * FNV_PRIME) & MASK32  # (2) 흩뜨리기
        return h

    def _index(self, key) -> int:
        """해시값을 버킷 번호로 접는다. 버킷 수로 나눈 나머지."""
        return self._hash(key) % len(self._buckets)

    # ---- 공개 API ----
    def size(self) -> int:
        return self._size

    def __len__(self) -> int:
        return self._size

    @property
    def bucket_count(self) -> int:
        return len(self._buckets)

    def load_factor(self) -> float:
        return self._size / len(self._buckets)

    def put(self, key, value) -> None:
        """넣거나 덮어쓴다."""
        bucket = self._buckets[self._index(key)]
        for node in bucket.nodes():
            if node.data.key == key:
                node.data.value = value  # 이미 있으면 값만 교체
                return
        bucket.insert_front(_Pair(key, value))
        self._size += 1
        if self.load_factor() > MAX_LOAD_FACTOR:
            self._resize()

    def get(self, key, default=None):
        """값을 꺼낸다. 없으면 default."""
        bucket = self._buckets[self._index(key)]
        for node in bucket.nodes():
            if node.data.key == key:
                return node.data.value
        return default

    def contains(self, key) -> bool:
        bucket = self._buckets[self._index(key)]
        for node in bucket.nodes():
            if node.data.key == key:
                return True
        return False

    def remove(self, key) -> bool:
        """지웠으면 True, 원래 없었으면 False."""
        bucket = self._buckets[self._index(key)]
        for node in bucket.nodes():
            if node.data.key == key:
                bucket.remove_node(node)
                self._size -= 1
                return True
        return False

    def keys(self):
        """전체 키를 DynamicArray 로 돌려준다(순서는 보장하지 않는다)."""
        out = DynamicArray(max(8, self._size))
        for i in range(len(self._buckets)):
            for pair in self._buckets[i]:
                out.append(pair.key)
        return out

    def items(self):
        for i in range(len(self._buckets)):
            for pair in self._buckets[i]:
                yield pair.key, pair.value

    def clear(self) -> None:
        self.__init__()

    # ---- 내부 ----
    def _resize(self) -> None:
        """버킷을 2배로 늘리고 전부 다시 배치한다.

        왜 '다시 배치'가 필요한가:
            버킷 번호는 (해시값 % 버킷수)로 정해진다. 버킷 수가 바뀌면
            같은 키라도 들어갈 자리가 달라지므로, 전부 새로 계산해 옮겨야 한다.
            이 작업만 O(n) 이지만 자주 일어나지 않아서 평균은 여전히 O(1) 이다.
        """
        old = self._buckets
        new_count = len(old) * 2
        self._buckets = DynamicArray(new_count)
        for _ in range(new_count):
            self._buckets.append(DoublyLinkedList())
        for i in range(len(old)):
            for pair in old[i]:
                self._buckets[self._index(pair.key)].insert_front(pair)

    def __repr__(self) -> str:
        return f"HashMap(size={self._size}, buckets={len(self._buckets)})"
