"""자료구조 3종 단위 테스트 — 내장 자료형 없이 직접 구현한 것이 맞게 도는지 확인."""

import unittest

from miniredis.dynamic_array import DynamicArray
from miniredis.hash_map import HashMap
from miniredis.heap import MinHeap
from miniredis.linked_list import DoublyLinkedList


class TestDynamicArray(unittest.TestCase):
    def test_용량이_가득차면_2배로_늘어난다(self):
        arr = DynamicArray(2)
        self.assertEqual(arr.capacity, 2)
        arr.append("a"); arr.append("b")
        self.assertEqual(arr.capacity, 2)
        arr.append("c")                      # 여기서 확장
        self.assertEqual(arr.capacity, 4)
        self.assertEqual(list(arr), ["a", "b", "c"])

    def test_인덱스_읽기쓰기와_삭제(self):
        arr = DynamicArray()
        for ch in "abcd":
            arr.append(ch)
        arr[1] = "B"
        self.assertEqual(arr[1], "B")
        self.assertEqual(arr.remove_at(0), "a")
        self.assertEqual(list(arr), ["B", "c", "d"])
        self.assertEqual(arr.pop(), "d")

    def test_범위를_벗어나면_에러(self):
        arr = DynamicArray()
        with self.assertRaises(IndexError):
            arr.get(0)


class TestDoublyLinkedList(unittest.TestCase):
    def test_앞뒤_삽입과_삭제(self):
        dll = DoublyLinkedList()
        dll.insert_back("b")
        dll.insert_front("a")
        dll.insert_back("c")
        self.assertEqual(list(dll), ["a", "b", "c"])
        self.assertEqual(dll.remove_front(), "a")
        self.assertEqual(dll.remove_back(), "c")
        self.assertEqual(list(dll), ["b"])

    def test_move_to_front_가_LRU의_핵심(self):
        dll = DoublyLinkedList()
        n1 = dll.insert_back(1)
        dll.insert_back(2)
        n3 = dll.insert_back(3)
        dll.move_to_front(n3)
        self.assertEqual(list(dll), [3, 1, 2])
        dll.move_to_front(n3)                 # 이미 맨 앞이면 그대로
        self.assertEqual(list(dll), [3, 1, 2])
        dll.move_to_front(n1)
        self.assertEqual(list(dll), [1, 3, 2])

    def test_중간_노드를_O1로_제거(self):
        dll = DoublyLinkedList()
        dll.insert_back("a")
        mid = dll.insert_back("b")
        dll.insert_back("c")
        self.assertEqual(dll.remove_node(mid), "b")
        self.assertEqual(list(dll), ["a", "c"])
        self.assertEqual(len(dll), 2)

    def test_빈_리스트는_None을_돌려준다(self):
        dll = DoublyLinkedList()
        self.assertIsNone(dll.remove_front())
        self.assertIsNone(dll.remove_back())
        self.assertTrue(dll.is_empty())


class TestHashMap(unittest.TestCase):
    def test_기본_넣고_빼기(self):
        m = HashMap()
        m.put("a", 1)
        m.put("b", 2)
        self.assertEqual(m.get("a"), 1)
        self.assertTrue(m.contains("b"))
        self.assertFalse(m.contains("zzz"))
        self.assertIsNone(m.get("zzz"))
        self.assertTrue(m.remove("a"))
        self.assertFalse(m.remove("a"))
        self.assertEqual(m.size(), 1)

    def test_같은_키는_덮어쓰고_개수는_안_늘어난다(self):
        m = HashMap()
        m.put("k", 1)
        m.put("k", 2)
        self.assertEqual(m.get("k"), 2)
        self.assertEqual(m.size(), 1)

    def test_로드팩터_0_75를_넘으면_버킷이_2배(self):
        m = HashMap(initial_buckets=4)
        self.assertEqual(m.bucket_count, 4)
        for i in range(4):                    # 4/4 = 1.0 > 0.75 → 중간에 확장
            m.put(f"k{i}", i)
        self.assertGreater(m.bucket_count, 4)
        self.assertLessEqual(m.load_factor(), 0.75)
        for i in range(4):                    # 확장 후에도 전부 찾을 수 있어야 한다
            self.assertEqual(m.get(f"k{i}"), i)

    def test_해시는_글자_순서를_구분한다(self):
        # 단순 합산 해시라면 같은 값이 나왔을 것이다
        self.assertNotEqual(HashMap._hash("abc"), HashMap._hash("cba"))

    def test_많이_넣어도_전부_보존된다(self):
        m = HashMap()
        for i in range(500):
            m.put(f"key{i}", i)
        self.assertEqual(m.size(), 500)
        self.assertEqual(len(m.keys()), 500)
        for i in range(0, 500, 37):
            self.assertEqual(m.get(f"key{i}"), i)


class TestMinHeap(unittest.TestCase):
    def test_항상_가장_작은_것이_먼저_나온다(self):
        h = MinHeap()
        for v in [5, 3, 8, 1, 9, 2]:
            h.push(v)
        self.assertEqual(h.peek(), 1)
        self.assertEqual([h.pop() for _ in range(6)], [1, 2, 3, 5, 8, 9])

    def test_튜플은_앞칸부터_비교된다(self):
        h = MinHeap()
        h.push((100, "late"))
        h.push((10, "early"))
        h.push((50, "mid"))
        self.assertEqual(h.peek(), (10, "early"))

    def test_빈_힙(self):
        h = MinHeap()
        self.assertTrue(h.is_empty())
        self.assertIsNone(h.peek())
        self.assertIsNone(h.pop())


if __name__ == "__main__":
    unittest.main()
