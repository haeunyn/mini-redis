# 설계 메모 — 왜 이렇게 만들었는가

## 1. 모듈을 왜 이렇게 쪼갰나

```
dynamic_array.py  배열          — 해시맵 버킷 테이블, 힙 내부 저장소가 쓴다
linked_list.py    이중 연결 리스트 — 해시맵 체이닝, LRU 줄이 쓴다
hash_map.py       해시맵         — 키 → Entry
heap.py           최소 힙        — TTL 만료 순서
adt.py            스택/큐/덱     — 연결 리스트 재활용 (보너스 2)
binary_tree.py    이진 트리/BST  — 힙의 배경 이해 (보너스 3·4)
pubsub.py         Pub/Sub       — 큐 재활용 (보너스 5)
store.py          저장소 엔진    — 위 셋을 조립 + 메모리/LRU/TTL 정책
parser.py         토큰 분리
commands.py       명령어 → Redis 스타일 출력
cli.py            REPL
errors.py         에러 메시지 표준
```

**아래쪽은 위쪽을 모른다.** `linked_list.py` 는 Redis 를 전혀 모르고,
`store.py` 는 CLI 를 전혀 모른다. 그래서 CLI 없이도 테스트할 수 있고,
자료구조만 따로 떼어 다른 곳에 쓸 수도 있다.

## 2. 가장 중요한 설계 결정 — `Entry.lru_node`

LRU 캐시의 교과서적인 질문: **"어떻게 O(1) 인가?"**

| 자료구조만 쓰면 | 문제 |
|---|---|
| 해시맵만 | "가장 오래 안 쓴 키"를 찾으려면 전부 훑어야 함 → O(n) |
| 연결 리스트만 | "이 키가 줄 어디 있지?"를 찾으려면 훑어야 함 → O(n) |

**해결:** 해시맵의 값(Entry)이 **자기가 LRU 줄에서 서 있는 노드를 직접 가리킨다.**

```
HashMap:  "user:1" ──→ Entry(value="Alice", lru_node=●)
                                               │
LRU 줄:   [head] ⇄ ● ⇄ ○ ⇄ ○ ⇄ [tail]
                   ↑              ↑
                 최신          가장 오래됨 (희생자)
```

- 키로 Entry 찾기 → 해시맵, O(1)
- Entry 에서 노드 꺼내 맨 앞으로 옮기기 → `move_to_front`, O(1)
- 희생자 찾기 → 줄의 맨 뒤, O(1)

## 3. TTL 에 왜 힙을 썼나 — 그리고 '게으른 삭제'

TTL 이 걸린 키가 1만 개여도 궁금한 건 하나다. **"가장 먼저 만료될 키는?"**
최솟값 하나만 빠르게 꺼내는 일 = 힙이 가장 잘하는 일. `peek()` 가 O(1) 이라
아직 만료 안 됐으면 **거기서 멈추면 된다.** 나머지는 볼 필요가 없다.

**문제:** `EXPIRE` 를 다시 걸거나 키를 지우면 힙에 옛 항목이 남는다.
힙 중간에서 특정 항목을 찾아 빼는 건 O(n) 이라 비싸다.

**해결 — lazy deletion(게으른 삭제):** 지우지 않고 **꺼낼 때 확인**한다.

```python
entry = self._map.get(key)
if entry is not None and entry.expire_at == expire_at:
    self._drop(entry)      # 진짜 만료
# 아니면 유령 항목이므로 그냥 버린다
```

만료 시각이 지금 Entry 의 것과 다르면 **유령**이다. 이쪽이 훨씬 싸다.

## 4. `used_memory` 는 왜 직접 세나

명세가 정한 공식:

```
used_memory = Σ( len(utf8(key)) + len(utf8(value)) )
```

노드·포인터·버킷 같은 **자료구조 오버헤드는 제외**한다.
실제 메모리가 아니라 **"정책을 적용하기 위한 회계 단위"** 라서 그렇다.
한글은 UTF-8 에서 글자당 3바이트이므로 `len(문자열)` 이 아니라
`len(문자열.encode('utf-8'))` 로 세야 한다. (`store.py` 의 `_utf8_len`)

## 5. 시계를 주입받는 이유

```python
def __init__(self, clock=time.time):
```

TTL 테스트에서 **진짜 3초를 기다리지 않기 위해서**다. 테스트는 가짜 시계를
넣고 `advance(4)` 로 시간을 돌려버린다. 덕분에 45개 테스트가 0.01초에 끝난다.

실행할 때는 기본값인 `time.time` 이 그대로 쓰이므로 동작은 동일하다.

## 6. 제약 지키기 — dict / set / collections 없이

| 필요했던 것 | 대신 쓴 것 |
|---|---|
| `dict` | `HashMap` (직접 구현, 체이닝) |
| `collections.deque` | `DoublyLinkedList` / `Deque` |
| `heapq` | `MinHeap` (직접 구현) |
| 가변 배열 | `DynamicArray` (고정 길이 리스트 + 2배 확장) |

파이썬 `list` 는 **고정 길이 배열 + 인덱스 접근** 수준으로만 썼다
(`[None] * capacity` 를 만들고 `arr[i]` 로만 접근). 확장 로직은 직접 구현했다.
