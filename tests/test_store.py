"""저장소/명령어 테스트 — LRU 제거, TTL 만료, 에러 표준을 검증한다.

TTL 테스트에서 실제로 3초를 기다리지 않는 비결:
    Store 가 clock 함수를 주입받도록 만들어 두었다. 가짜 시계를 넣고
    원하는 만큼 시간을 '돌려버리면' 만료를 즉시 재현할 수 있다.
"""

import unittest

from miniredis.commands import CommandExecutor
from miniredis.store import Store


class FakeClock:
    """테스트용 가짜 시계. advance() 로 시간을 앞으로 돌린다."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestLRUEviction(unittest.TestCase):
    def test_명세_예시_그대로_재현된다(self):
        ex = CommandExecutor()
        self.assertEqual(ex.execute_line("CONFIG SET maxmemory 30"), "OK")
        self.assertEqual(ex.execute_line('SET user:1 "Alice"'), "OK")
        self.assertEqual(ex.execute_line('SET user:2 "Bob"'), "OK")
        self.assertEqual(ex.execute_line('SET user:3 "Charlie"'), "OK")
        # user:1 이 가장 오래 안 쓰였으므로 쫓겨난다
        self.assertEqual(ex.execute_line("GET user:1"), "(nil)")
        self.assertEqual(
            ex.execute_line("INFO memory"),
            "used_memory:22\nmaxmemory:30\nevicted_keys:1",
        )

    def test_GET하면_LRU순서가_바뀌어_희생자가_달라진다(self):
        ex = CommandExecutor()
        ex.execute_line("CONFIG SET maxmemory 30")
        ex.execute_line('SET user:1 "Alice"')
        ex.execute_line('SET user:2 "Bob"')
        ex.execute_line("GET user:1")          # user:1 을 최신으로 끌어올린다
        ex.execute_line('SET user:3 "Charlie"')
        self.assertEqual(ex.execute_line("GET user:1"), '"Alice"')
        self.assertEqual(ex.execute_line("GET user:2"), "(nil)")  # 이번엔 user:2

    def test_단일항목이_한도보다_크면_저장하지_않고_OOM(self):
        ex = CommandExecutor()
        ex.execute_line("CONFIG SET maxmemory 5")
        out = ex.execute_line('SET key "아주아주긴값입니다"')
        self.assertIn("OOM", out)
        self.assertEqual(ex.execute_line("DBSIZE"), "(integer) 0")

    def test_maxmemory_0은_무제한(self):
        ex = CommandExecutor()
        for i in range(50):
            ex.execute_line(f'SET k{i} "v{i}"')
        self.assertEqual(ex.execute_line("DBSIZE"), "(integer) 50")

    def test_한글값은_utf8_바이트로_센다(self):
        store = Store()
        store.set("이름", "하은")          # 2글자*3 + 2글자*3 = 12바이트
        self.assertEqual(store.used_memory, 12)


class TestTTL(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.ex = CommandExecutor(Store(clock=self.clock))

    def test_만료되면_GET이_nil이고_TTL은_마이너스2(self):
        self.ex.execute_line('SET user:2 "Bob"')
        self.assertEqual(self.ex.execute_line("EXPIRE user:2 3"), "(integer) 1")
        self.assertEqual(self.ex.execute_line("TTL user:2"), "(integer) 3")
        self.clock.advance(4)                   # 4초 경과
        self.assertEqual(self.ex.execute_line("GET user:2"), "(nil)")
        self.assertEqual(self.ex.execute_line("TTL user:2"), "(integer) -2")

    def test_TTL이_없는_키는_마이너스1(self):
        self.ex.execute_line('SET k "v"')
        self.assertEqual(self.ex.execute_line("TTL k"), "(integer) -1")

    def test_없는_키에_EXPIRE하면_0(self):
        self.assertEqual(self.ex.execute_line("EXPIRE 없는키 10"), "(integer) 0")

    def test_SET으로_덮어쓰면_TTL이_초기화된다(self):
        self.ex.execute_line('SET k "v1"')
        self.ex.execute_line("EXPIRE k 10")
        self.ex.execute_line('SET k "v2"')      # 명세: 기존 TTL 삭제
        self.assertEqual(self.ex.execute_line("TTL k"), "(integer) -1")

    def test_0이하_EXPIRE는_즉시_만료(self):
        self.ex.execute_line('SET k "v"')
        self.assertEqual(self.ex.execute_line("EXPIRE k 0"), "(integer) 1")
        self.assertEqual(self.ex.execute_line("GET k"), "(nil)")

    def test_만료된_키는_DBSIZE와_KEYS에서_사라진다(self):
        self.ex.execute_line('SET a "1"')
        self.ex.execute_line('SET b "2"')
        self.ex.execute_line("EXPIRE a 5")
        self.assertEqual(self.ex.execute_line("DBSIZE"), "(integer) 2")
        self.clock.advance(6)
        self.assertEqual(self.ex.execute_line("DBSIZE"), "(integer) 1")
        self.assertEqual(self.ex.execute_line("KEYS"), '1. "b"')

    def test_만료된_키의_GET은_LRU를_갱신하지_않는다(self):
        store = Store(clock=self.clock)
        store.set("old", "1")
        store.set("new", "2")
        store.expire("old", 5)
        self.clock.advance(6)
        self.assertIsNone(store.get("old"))     # 만료 → 삭제, LRU 갱신 없음
        self.assertEqual(store.dbsize(), 1)


class TestCommandErrors(unittest.TestCase):
    def setUp(self):
        self.ex = CommandExecutor()

    def test_모르는_명령어(self):
        self.assertEqual(
            self.ex.execute_line("HELLO"), "(error) ERR unknown command 'HELLO'"
        )

    def test_인자_개수_오류(self):
        self.assertEqual(
            self.ex.execute_line("GET"),
            "(error) ERR wrong number of arguments for 'GET' command",
        )
        self.assertIn("wrong number", self.ex.execute_line("SET onlykey"))

    def test_정수_파싱_실패(self):
        self.assertEqual(
            self.ex.execute_line("CONFIG SET maxmemory abc"),
            "(error) ERR value is not an integer or out of range",
        )
        self.assertIn("not an integer", self.ex.execute_line("EXPIRE k 삼초"))

    def test_빈_줄은_아무것도_출력하지_않는다(self):
        self.assertEqual(self.ex.execute_line("   "), "")

    def test_따옴표_안의_공백은_하나의_값(self):
        self.ex.execute_line('SET name "Alice Kim"')
        self.assertEqual(self.ex.execute_line("GET name"), '"Alice Kim"')

    def test_명령어는_대소문자를_가리지_않는다(self):
        self.assertEqual(self.ex.execute_line('set k "v"'), "OK")
        self.assertEqual(self.ex.execute_line("GeT k"), '"v"')


class TestBasicCommands(unittest.TestCase):
    def setUp(self):
        self.ex = CommandExecutor()

    def test_DEL과_EXISTS(self):
        self.ex.execute_line('SET k "v"')
        self.assertEqual(self.ex.execute_line("EXISTS k"), "(integer) 1")
        self.assertEqual(self.ex.execute_line("DEL k"), "(integer) 1")
        self.assertEqual(self.ex.execute_line("DEL k"), "(integer) 0")
        self.assertEqual(self.ex.execute_line("EXISTS k"), "(integer) 0")

    def test_DEL은_메모리도_돌려놓는다(self):
        store = Store()
        store.set("k", "value")
        before = store.used_memory
        store.delete("k")
        self.assertEqual(store.used_memory, 0)
        self.assertGreater(before, 0)

    def test_빈_KEYS(self):
        self.assertEqual(self.ex.execute_line("KEYS"), "(empty array)")


if __name__ == "__main__":
    unittest.main()


class TestBonusStructures(unittest.TestCase):
    """보너스 과제 3·4 — 이진 트리 순회와 BST."""

    def setUp(self):
        from miniredis.binary_tree import BST
        self.bst = BST()
        for v in [50, 30, 70, 20, 40, 60, 80]:
            self.bst.insert(v)

    def test_중위순회는_정렬된_결과를_준다(self):
        self.assertEqual(self.bst.inorder(), [20, 30, 40, 50, 60, 70, 80])

    def test_순회_4종(self):
        self.assertEqual(self.bst.preorder(), [50, 30, 20, 40, 70, 60, 80])
        self.assertEqual(self.bst.postorder(), [20, 40, 30, 60, 80, 70, 50])
        self.assertEqual(self.bst.level_order(), [50, 30, 70, 20, 40, 60, 80])
        self.assertEqual(self.bst.height(), 3)

    def test_탐색(self):
        self.assertTrue(self.bst.search(40))
        self.assertFalse(self.bst.search(99))

    def test_삭제_세_경우(self):
        self.bst.delete(20)                     # 자식 없음
        self.assertEqual(self.bst.inorder(), [30, 40, 50, 60, 70, 80])
        self.bst.delete(30)                     # 자식 하나
        self.assertEqual(self.bst.inorder(), [40, 50, 60, 70, 80])
        self.bst.delete(70)                     # 자식 둘
        self.assertEqual(self.bst.inorder(), [40, 50, 60, 80])


class TestBonusADT(unittest.TestCase):
    """보너스 과제 2 — 스택/큐/덱."""

    def test_스택은_LIFO(self):
        from miniredis.adt import Stack
        s = Stack()
        for v in [1, 2, 3]:
            s.push(v)
        self.assertEqual(s.peek(), 3)
        self.assertEqual([s.pop() for _ in range(3)], [3, 2, 1])
        self.assertTrue(s.is_empty())

    def test_큐는_FIFO(self):
        from miniredis.adt import Queue
        q = Queue()
        for v in [1, 2, 3]:
            q.enqueue(v)
        self.assertEqual(q.drain(), [1, 2, 3])

    def test_덱은_양쪽(self):
        from miniredis.adt import Deque
        d = Deque()
        d.push_back(2); d.push_front(1); d.push_back(3)
        self.assertEqual((d.pop_front(), d.pop_back()), (1, 3))
        self.assertEqual(len(d), 1)


class TestBonusPubSub(unittest.TestCase):
    """보너스 과제 5 — Pub/Sub."""

    def test_구독한_채널의_메시지만_받는다(self):
        ex = CommandExecutor()
        ex.execute_line("SUBSCRIBE news")
        out = ex.execute_line('PUBLISH news "hello"')
        self.assertIn("(integer) 1", out)
        self.assertIn('"hello"', out)
        self.assertEqual(ex.execute_line('PUBLISH other "x"'), "(integer) 0")

    def test_해지하면_더이상_받지_않는다(self):
        ex = CommandExecutor()
        ex.execute_line("SUBSCRIBE news")
        ex.execute_line("UNSUBSCRIBE news")
        self.assertEqual(ex.execute_line('PUBLISH news "x"'), "(integer) 0")
