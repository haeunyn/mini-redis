"""동적 배열 — 보너스 과제 1.

파이썬 list 의 append 를 쓰지 않고 "고정 길이 배열 + 인덱스 접근"만으로
직접 구현한다. 용량이 차면 2배로 늘린다.

왜 직접 만드는가:
    해시맵의 버킷 테이블과 힙의 내부 저장소가 모두 "인덱스로 접근하는 배열"이
    필요하다. 그 배열이 어떻게 커지는지를 눈으로 보려고 밑바닥부터 만든다.
"""


class DynamicArray:
    """용량이 꽉 차면 2배로 늘어나는 배열."""

    def __init__(self, capacity: int = 8) -> None:
        # 고정 길이 저장소. 제약사항이 허용하는 "인덱스 접근 수준"으로만 쓴다.
        # (append/insert/pop 같은 list 메서드는 사용하지 않는다)
        self._slots = [None] * max(1, capacity)
        self._size = 0

    # ---- 조회 ----
    def __len__(self) -> int:
        return self._size

    @property
    def capacity(self) -> int:
        return len(self._slots)

    def get(self, index: int):
        self._check(index)
        return self._slots[index]

    def set(self, index: int, value) -> None:
        self._check(index)
        self._slots[index] = value

    def __getitem__(self, index: int):
        return self.get(index)

    def __setitem__(self, index: int, value) -> None:
        self.set(index, value)

    def __iter__(self):
        for i in range(self._size):
            yield self._slots[i]

    # ---- 변경 ----
    def append(self, value) -> None:
        """맨 뒤에 추가. 평균 O(1) (확장이 일어나는 순간만 O(n))."""
        if self._size == len(self._slots):
            self._grow()
        self._slots[self._size] = value
        self._size += 1

    def pop(self):
        """맨 뒤 원소를 꺼낸다. O(1)."""
        if self._size == 0:
            raise IndexError("pop from empty DynamicArray")
        self._size -= 1
        value = self._slots[self._size]
        self._slots[self._size] = None  # 참조를 끊어 메모리 누수를 막는다
        return value

    def remove_at(self, index: int):
        """index 를 지우고 뒤를 한 칸씩 당긴다. O(n)."""
        self._check(index)
        value = self._slots[index]
        for i in range(index, self._size - 1):
            self._slots[i] = self._slots[i + 1]
        self._size -= 1
        self._slots[self._size] = None
        return value

    def clear(self) -> None:
        self._slots = [None] * 8
        self._size = 0

    # ---- 내부 ----
    def _grow(self) -> None:
        """용량 2배 확장. 새 배열을 만들고 기존 값을 옮겨 담는다."""
        bigger = [None] * (len(self._slots) * 2)
        for i in range(self._size):
            bigger[i] = self._slots[i]
        self._slots = bigger

    def _check(self, index: int) -> None:
        if not 0 <= index < self._size:
            raise IndexError(f"index {index} out of range (size={self._size})")

    def __repr__(self) -> str:
        return f"DynamicArray({[self._slots[i] for i in range(self._size)]})"
