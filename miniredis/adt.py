"""스택 / 큐 / 덱 — 보너스 과제 2.

셋 다 "어디로 넣고 어디로 빼는가"만 다른 형제들이다.
이중 연결 리스트가 이미 양쪽 끝 삽입/삭제를 O(1) 로 지원하므로,
새로 짤 것 없이 '어느 쪽 문만 열어둘지'를 정해주면 된다.

    스택(Stack) : 한쪽 문만 사용      → 나중에 넣은 게 먼저 나온다 (LIFO)
    큐(Queue)   : 뒤로 넣고 앞으로 뺀다 → 먼저 넣은 게 먼저 나온다 (FIFO)
    덱(Deque)   : 양쪽 문 모두 사용     → 둘 다 가능

자세한 비교는 docs/STACK_QUEUE_DEQUE.md 참고.
"""

from .linked_list import DoublyLinkedList


class Stack:
    """LIFO. 되돌리기(Undo), 괄호 검사, 함수 호출 스택에 쓰인다."""

    def __init__(self) -> None:
        self._items = DoublyLinkedList()

    def push(self, item) -> None:
        self._items.insert_front(item)

    def pop(self):
        return self._items.remove_front()

    def peek(self):
        return self._items.front()

    def is_empty(self) -> bool:
        return self._items.is_empty()

    def __len__(self) -> int:
        return len(self._items)


class Queue:
    """FIFO. 작업 대기열, Pub/Sub 메시지 버퍼에 쓰인다."""

    def __init__(self) -> None:
        self._items = DoublyLinkedList()

    def enqueue(self, item) -> None:
        self._items.insert_back(item)   # 뒤로 들어와서

    def dequeue(self):
        return self._items.remove_front()  # 앞으로 나간다

    def peek(self):
        return self._items.front()

    def is_empty(self) -> bool:
        return self._items.is_empty()

    def __len__(self) -> int:
        return len(self._items)

    def drain(self):
        """쌓인 것을 전부 꺼내 리스트로 돌려준다(Pub/Sub 수신함 비우기용)."""
        out = []
        while not self.is_empty():
            out.append(self.dequeue())
        return out


class Deque:
    """양쪽 끝에서 넣고 뺄 수 있는 줄. 이 프로젝트의 LRU 가 사실상 덱이다."""

    def __init__(self) -> None:
        self._items = DoublyLinkedList()

    def push_front(self, item) -> None:
        self._items.insert_front(item)

    def push_back(self, item) -> None:
        self._items.insert_back(item)

    def pop_front(self):
        return self._items.remove_front()

    def pop_back(self):
        return self._items.remove_back()

    def front(self):
        return self._items.front()

    def back(self):
        return self._items.back()

    def is_empty(self) -> bool:
        return self._items.is_empty()

    def __len__(self) -> int:
        return len(self._items)
