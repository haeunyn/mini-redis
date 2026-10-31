"""이중 연결 리스트 — 모든 삽입/삭제/이동이 O(1).

두 군데에서 쓴다:
    1) 해시맵의 충돌 해결(체이닝) — 같은 버킷에 모인 항목들을 담는 줄
    2) LRU 추적 — 최근 쓴 키를 앞으로 보내는 줄

왜 "이중" 연결인가:
    단일 연결 리스트는 어떤 노드를 지우려면 "그 앞 노드"를 알아야 해서
    처음부터 훑어야 한다 → O(n). 각 노드가 prev 를 들고 있으면 자기 앞뒤를
    바로 알 수 있어서, 노드만 손에 쥐고 있으면 O(1) 에 뗄 수 있다.
    LRU 는 "방금 쓴 키를 맨 앞으로 옮기는" 일을 매번 하므로 이게 핵심이다.
"""


class Node:
    """연결 리스트의 한 칸."""

    __slots__ = ("prev", "next", "data")

    def __init__(self, data=None) -> None:
        self.prev = None
        self.next = None
        self.data = data

    def __repr__(self) -> str:
        return f"Node({self.data!r})"


class DoublyLinkedList:
    """양쪽 끝에 보초(sentinel) 노드를 둔 이중 연결 리스트.

    보초를 두는 이유:
        맨 앞/맨 뒤에 넣거나 뺄 때 "리스트가 비었나?", "이게 마지막 노드인가?"
        같은 None 분기가 전부 사라진다. 실제 데이터 노드는 항상 양옆에
        이웃이 있다고 가정할 수 있어서 코드가 짧아지고 버그가 줄어든다.
    """

    def __init__(self) -> None:
        self._head = Node()  # 보초: 실제 데이터 아님
        self._tail = Node()  # 보초: 실제 데이터 아님
        self._head.next = self._tail
        self._tail.prev = self._head
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self._size == 0

    # ---- 삽입 ----
    def insert_front(self, data) -> Node:
        """맨 앞에 넣고 노드를 돌려준다. O(1)."""
        return self._insert_after(self._head, Node(data))

    def insert_back(self, data) -> Node:
        """맨 뒤에 넣고 노드를 돌려준다. O(1)."""
        return self._insert_after(self._tail.prev, Node(data))

    # ---- 삭제 ----
    def remove_front(self):
        """맨 앞 데이터를 꺼낸다. 비었으면 None. O(1)."""
        if self.is_empty():
            return None
        return self.remove_node(self._head.next)

    def remove_back(self):
        """맨 뒤 데이터를 꺼낸다. 비었으면 None. O(1). LRU 제거가 여기를 쓴다."""
        if self.is_empty():
            return None
        return self.remove_node(self._tail.prev)

    def remove_node(self, node: Node):
        """노드를 줄에서 뗀다. 노드를 이미 손에 쥐고 있으므로 O(1).

        앞뒤 이웃끼리 손을 잡게 하면 이 노드는 줄에서 빠진다.
        """
        if node is self._head or node is self._tail:
            raise ValueError("보초 노드는 제거할 수 없습니다")
        node.prev.next = node.next
        node.next.prev = node.prev
        node.prev = None
        node.next = None
        self._size -= 1
        return node.data

    # ---- 이동 ----
    def move_to_front(self, node: Node) -> None:
        """이미 줄에 있는 노드를 맨 앞으로 옮긴다. O(1).

        LRU 의 심장. "방금 이 키를 썼다"를 표시하는 동작이다.
        떼고(detach) 다시 붙이는(attach) 두 단계인데 둘 다 포인터 몇 개만
        바꾸므로 리스트가 아무리 길어도 시간이 늘지 않는다.
        """
        if node.prev is self._head:
            return  # 이미 맨 앞이면 할 일 없음
        # 1) 뗀다
        node.prev.next = node.next
        node.next.prev = node.prev
        # 2) 맨 앞에 붙인다
        node.prev = self._head
        node.next = self._head.next
        self._head.next.prev = node
        self._head.next = node

    # ---- 조회 ----
    def front(self):
        return None if self.is_empty() else self._head.next.data

    def back(self):
        return None if self.is_empty() else self._tail.prev.data

    def back_node(self):
        """맨 뒤 노드 자체를 돌려준다(LRU 희생자 찾기용). 비었으면 None."""
        return None if self.is_empty() else self._tail.prev

    def __iter__(self):
        """앞에서 뒤로 데이터를 훑는다."""
        cur = self._head.next
        while cur is not self._tail:
            yield cur.data
            cur = cur.next

    def nodes(self):
        """데이터가 아니라 노드를 훑는다(해시맵 체이닝 탐색용)."""
        cur = self._head.next
        while cur is not self._tail:
            nxt = cur.next  # 순회 중 제거해도 안전하도록 미리 잡아둔다
            yield cur
            cur = nxt

    # ---- 내부 ----
    def _insert_after(self, anchor: Node, node: Node) -> Node:
        node.prev = anchor
        node.next = anchor.next
        anchor.next.prev = node
        anchor.next = node
        self._size += 1
        return node

    def __repr__(self) -> str:
        return f"DoublyLinkedList({list(self)})"
