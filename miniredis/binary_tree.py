"""이진 트리와 이진 탐색 트리 — 보너스 과제 3, 4.

왜 이 미션에 이진 트리가 나오는가:
    힙이 바로 "완전 이진 트리를 배열로 표현한 것"이다.
    여기서 트리를 포인터로 직접 만들어 보면, 힙이 왜 배열만으로
    부모/자식을 찾을 수 있었는지가 선명해진다.
"""

from .adt import Queue


class TreeNode:
    __slots__ = ("value", "left", "right")

    def __init__(self, value) -> None:
        self.value = value
        self.left = None
        self.right = None

    def __repr__(self) -> str:
        return f"TreeNode({self.value!r})"


class BinaryTree:
    """순회 4종을 보여주기 위한 이진 트리.

    순회 이름은 '뿌리(root)를 언제 방문하는가'로 정해진다.
        전위(preorder)  : 뿌리 → 왼쪽 → 오른쪽   (트리 복사/직렬화에 쓰임)
        중위(inorder)   : 왼쪽 → 뿌리 → 오른쪽   (BST 면 정렬된 순서가 나옴)
        후위(postorder) : 왼쪽 → 오른쪽 → 뿌리   (자식부터 지워야 하는 삭제에 쓰임)
        레벨(level)     : 위에서 아래로 한 층씩  (큐를 쓴다 = BFS)
    """

    def __init__(self, root: TreeNode = None) -> None:
        self.root = root

    def preorder(self):
        out = []
        self._pre(self.root, out)
        return out

    def inorder(self):
        out = []
        self._in(self.root, out)
        return out

    def postorder(self):
        out = []
        self._post(self.root, out)
        return out

    def level_order(self):
        """층별 순회. 직접 만든 Queue 를 사용한다(재귀가 아니라 반복)."""
        out = []
        if self.root is None:
            return out
        q = Queue()
        q.enqueue(self.root)
        while not q.is_empty():
            node = q.dequeue()
            out.append(node.value)
            if node.left:
                q.enqueue(node.left)
            if node.right:
                q.enqueue(node.right)
        return out

    def height(self) -> int:
        return self._height(self.root)

    # ---- 내부 재귀 ----
    def _pre(self, node, out):
        if node:
            out.append(node.value)
            self._pre(node.left, out)
            self._pre(node.right, out)

    def _in(self, node, out):
        if node:
            self._in(node.left, out)
            out.append(node.value)
            self._in(node.right, out)

    def _post(self, node, out):
        if node:
            self._post(node.left, out)
            self._post(node.right, out)
            out.append(node.value)

    def _height(self, node) -> int:
        if node is None:
            return 0
        return 1 + max(self._height(node.left), self._height(node.right))


class BST(BinaryTree):
    """이진 탐색 트리 — 왼쪽은 나보다 작고, 오른쪽은 나보다 크다.

    이 규칙 덕분에 탐색이 '반씩 버리기'가 되어 평균 O(log n) 이다.
    중위 순회하면 저절로 오름차순이 나온다는 점이 가장 중요한 성질이다.
    (Redis 의 범위 조회/정렬 기능이 이런 구조 위에 세워진다)
    """

    def insert(self, value) -> None:
        self.root = self._insert(self.root, value)

    def search(self, value) -> bool:
        node = self.root
        while node is not None:
            if value == node.value:
                return True
            node = node.left if value < node.value else node.right
        return False

    def delete(self, value) -> None:
        self.root = self._delete(self.root, value)

    def _insert(self, node, value):
        if node is None:
            return TreeNode(value)
        if value < node.value:
            node.left = self._insert(node.left, value)
        elif value > node.value:
            node.right = self._insert(node.right, value)
        # 같은 값은 넣지 않는다
        return node

    def _delete(self, node, value):
        """삭제는 세 경우로 나뉜다 — BST 에서 가장 까다로운 부분.

        1) 자식이 없다      → 그냥 뗀다
        2) 자식이 하나다    → 그 자식을 내 자리에 올린다
        3) 자식이 둘이다    → 오른쪽 가지에서 '가장 작은 값'을 데려와 내 값을 덮고,
                              그 가장 작은 노드를 대신 지운다.
                              왜 그 값인가: 나보다 크면서 가장 가까운 값이라
                              BST 규칙이 그대로 유지되기 때문이다.
        """
        if node is None:
            return None
        if value < node.value:
            node.left = self._delete(node.left, value)
        elif value > node.value:
            node.right = self._delete(node.right, value)
        else:
            if node.left is None:
                return node.right
            if node.right is None:
                return node.left
            successor = node.right
            while successor.left is not None:
                successor = successor.left
            node.value = successor.value
            node.right = self._delete(node.right, successor.value)
        return node
