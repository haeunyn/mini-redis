"""최소 힙 — TTL(만료 시간) 관리를 위해 직접 구현.

왜 하필 힙인가:
    TTL 이 걸린 키가 1만 개 있어도, 우리가 매번 궁금한 건 딱 하나다.
    "가장 먼저 만료되는 키는 무엇인가?"
    - 전부 훑으면 O(n)
    - 매번 정렬해두면 삽입이 O(n log n)
    - 힙은 꺼내기가 O(log n), 넣기도 O(log n), 들여다보기(peek)는 O(1)
    "최솟값 하나만 빠르게"가 정확히 힙이 잘하는 일이다.

힙은 완전 이진 트리인데, 트리를 배열로 표현한다. 노드가 i 번이면
    부모 = (i - 1) // 2,  왼쪽 자식 = 2i + 1,  오른쪽 자식 = 2i + 2
포인터 없이 산수만으로 부모/자식을 찾을 수 있어서 빠르고 메모리도 적게 쓴다.
"""

from .dynamic_array import DynamicArray


class MinHeap:
    """가장 작은 원소가 항상 맨 위에 오는 힙.

    원소는 서로 비교만 가능하면 된다.
    이 프로젝트에서는 (expire_at, key) 꼴의 튜플을 넣는다.
    튜플 비교는 앞에서부터 하므로 자연히 '만료 시각이 이른 순'이 된다.
    """

    def __init__(self) -> None:
        self._items = DynamicArray()

    def size(self) -> int:
        return len(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def peek(self):
        """맨 위(가장 작은) 원소를 보기만 한다. O(1). 비었으면 None."""
        return None if self.is_empty() else self._items[0]

    def push(self, item) -> None:
        """넣는다. O(log n).

        맨 뒤에 붙인 뒤, 부모보다 작으면 계속 위로 올라간다.
        """
        self._items.append(item)
        self._heapify_up(len(self._items) - 1)

    def pop(self):
        """가장 작은 원소를 꺼낸다. O(log n). 비었으면 None.

        맨 위를 빼고 그 자리에 '맨 뒤'를 올린 뒤, 자식보다 크면 내려보낸다.
        왜 맨 뒤를 올리나: 트리 모양(완전 이진 트리)을 깨지 않는 유일한 선택이다.
        """
        if self.is_empty():
            return None
        top = self._items[0]
        last = self._items.pop()
        if len(self._items) > 0:
            self._items[0] = last
            self._heapify_down(0)
        return top

    # ---- 내부: 위로 올리기 / 아래로 내리기 ----
    def _heapify_up(self, i: int) -> None:
        """i 번 원소를 제자리까지 끌어올린다."""
        while i > 0:
            parent = (i - 1) // 2
            if self._items[i] < self._items[parent]:
                self._swap(i, parent)
                i = parent
            else:
                break  # 부모보다 크면 이미 제자리

    def _heapify_down(self, i: int) -> None:
        """i 번 원소를 제자리까지 내려보낸다."""
        n = len(self._items)
        while True:
            left, right = 2 * i + 1, 2 * i + 2
            smallest = i
            if left < n and self._items[left] < self._items[smallest]:
                smallest = left
            if right < n and self._items[right] < self._items[smallest]:
                smallest = right
            if smallest == i:
                break  # 두 자식보다 작으면 제자리
            self._swap(i, smallest)
            i = smallest

    def _swap(self, a: int, b: int) -> None:
        self._items[a], self._items[b] = self._items[b], self._items[a]

    def __repr__(self) -> str:
        return f"MinHeap({[self._items[i] for i in range(len(self._items))]})"
