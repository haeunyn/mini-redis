"""Pub/Sub — 보너스 과제 5.

구독자별 '수신함'을 큐로 만든다. 직접 구현한 Queue(=이중 연결 리스트)를
메시지 버퍼로 재활용하는 것이 이 보너스의 핵심이다.

    PUBLISH  채널에 메시지를 뿌린다 → 구독 중인 모든 수신함에 enqueue
    SUBSCRIBE 채널을 구독한다 → 그 채널의 구독자 목록에 내 수신함을 등록

네트워크가 없는 CLI 환경이므로 구독자는 '이 세션' 하나뿐이다.
그래도 구조는 여러 구독자를 전제로 만들어 두었다.
"""

from .adt import Queue
from .hash_map import HashMap
from .linked_list import DoublyLinkedList


class Subscriber:
    """구독자 한 명. 자기 수신함(큐)을 들고 있다."""

    __slots__ = ("name", "inbox")

    def __init__(self, name: str) -> None:
        self.name = name
        self.inbox = Queue()

    def __repr__(self) -> str:
        return f"Subscriber({self.name!r}, pending={len(self.inbox)})"


class PubSub:
    def __init__(self) -> None:
        # 채널 이름 -> 구독자들의 연결 리스트
        self._channels = HashMap()

    def subscribe(self, channel: str, subscriber: Subscriber) -> int:
        """구독한다. 그 구독자가 지금 구독 중인 채널 수를 돌려준다."""
        subs = self._channels.get(channel)
        if subs is None:
            subs = DoublyLinkedList()
            self._channels.put(channel, subs)
        for existing in subs:
            if existing is subscriber:
                return self.subscription_count(subscriber)  # 중복 구독 무시
        subs.insert_back(subscriber)
        return self.subscription_count(subscriber)

    def unsubscribe(self, channel: str, subscriber: Subscriber) -> bool:
        subs = self._channels.get(channel)
        if subs is None:
            return False
        for node in subs.nodes():
            if node.data is subscriber:
                subs.remove_node(node)
                if subs.is_empty():
                    self._channels.remove(channel)
                return True
        return False

    def publish(self, channel: str, message: str) -> int:
        """메시지를 뿌리고 받은 구독자 수를 돌려준다."""
        subs = self._channels.get(channel)
        if subs is None:
            return 0
        count = 0
        for subscriber in subs:
            subscriber.inbox.enqueue((channel, message))
            count += 1
        return count

    def subscription_count(self, subscriber: Subscriber) -> int:
        total = 0
        for _, subs in self._channels.items():
            for existing in subs:
                if existing is subscriber:
                    total += 1
        return total

    def channels(self):
        arr = self._channels.keys()
        return [arr[i] for i in range(len(arr))]
