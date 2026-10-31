# Mini Redis

코디세이 본과정 미션 **B5-1 — 정보를 엄청 빠르게 찾아주는 작은 저장소 만들기**

해시맵 · 이중 연결 리스트 · 최소 힙을 **밑바닥부터 직접 구현**해서 만든
CLI 기반 인메모리 Key-Value 저장소입니다.
`dict` · `set` · `collections` 를 쓰지 않았습니다.

## 실행

```bash
./run.sh          # 대화형 REPL
./run.sh demo     # 데모 스크립트 자동 실행
./run.sh test     # 테스트 45개 실행
```

Python 3.8 이상이면 되고, 외부 패키지는 쓰지 않습니다.

```
$ ./run.sh
mini-redis> SET user:1 "Alice"
OK
mini-redis> GET user:1
"Alice"
mini-redis> exit
```

## 지원 명령어

| 분류 | 명령어 | 설명 |
|---|---|---|
| String (6) | `SET key value` | 저장. 성공 시 LRU 갱신 |
| | `GET key` | 조회. 성공 시에만 LRU 갱신 |
| | `DEL key` | 삭제 (데이터·LRU·TTL 모두에서) |
| | `EXISTS key` | 존재 여부 |
| | `DBSIZE` | 전체 키 개수 |
| | `KEYS` | 전체 키 목록 |
| 메모리 (2) | `CONFIG SET maxmemory <bytes>` | 한도 설정 (0 = 무제한) |
| | `INFO memory` | 사용량 / 한도 / 제거된 키 수 |
| TTL (2) | `EXPIRE key seconds` | 만료 시간 설정 |
| | `TTL key` | 남은 시간 (-1 = 무기한, -2 = 없는 키) |
| 보너스 | `SUBSCRIBE` / `UNSUBSCRIBE` / `PUBLISH` | Pub/Sub |

출력은 Redis 스타일을 따릅니다 — `OK`, `(nil)`, `(integer) N`, `(error) ...`

## 동작 예시

```
mini-redis> CONFIG SET maxmemory 30
OK
mini-redis> SET user:1 "Alice"
OK
mini-redis> SET user:2 "Bob"
OK
mini-redis> SET user:3 "Charlie"
OK
mini-redis> GET user:1          ← 한도 초과로 가장 오래된 user:1 이 제거됨
(nil)
mini-redis> INFO memory
used_memory:22
maxmemory:30
evicted_keys:1
```

## 구조

```
miniredis/
├── dynamic_array.py   동적 배열      — 2배 확장 (보너스 1)
├── linked_list.py     이중 연결 리스트 — 모든 연산 O(1)
├── hash_map.py        해시맵         — 체이닝, 로드팩터 0.75 확장
├── heap.py            최소 힙        — TTL 만료 순서 관리
├── adt.py             스택/큐/덱      — 연결 리스트 재활용 (보너스 2)
├── binary_tree.py     이진 트리·BST   — 순회 4종 (보너스 3·4)
├── pubsub.py          Pub/Sub        — 큐 재활용 (보너스 5)
├── store.py           저장소 엔진     — 메모리·LRU·TTL 정책
├── parser.py          토큰 분리
├── commands.py        명령어 실행·출력 형식
├── cli.py             REPL
└── errors.py          에러 메시지 표준
```

설계 의도와 선택 이유는 **[docs/DESIGN.md](docs/DESIGN.md)** 에 정리했습니다.

## 핵심 아이디어 세 가지

**1. LRU 가 O(1) 인 이유 — 해시맵 + 연결 리스트**

해시맵만 쓰면 "가장 오래된 키"를 찾느라 O(n), 연결 리스트만 쓰면 "이 키가 어디
있는지" 찾느라 O(n)입니다. 해시맵의 값(`Entry`)이 **자기 LRU 노드를 직접 가리키게**
하면 양쪽 다 O(1)이 됩니다.

```
HashMap:  "user:1" ──→ Entry(value="Alice", lru_node=●)
                                               │
LRU 줄:   [head] ⇄ ● ⇄ ○ ⇄ ○ ⇄ [tail]
                   최신          가장 오래됨(희생자)
```

**2. TTL 에 힙을 쓰는 이유**

만료 키가 1만 개여도 궁금한 건 "가장 먼저 만료될 키" 하나뿐입니다. 힙의 `peek()`
는 O(1)이라, 맨 위가 아직 안 끝났으면 **나머지는 볼 필요가 없습니다.**

**3. 게으른 삭제 (lazy deletion)**

`EXPIRE` 를 다시 걸면 힙에 옛 항목이 남습니다. 힙 중간에서 빼는 건 O(n)이라
비싸므로, 지우지 않고 **꺼낼 때 "지금 Entry 의 만료 시각과 같은가"를 확인**해서
어긋나면 버립니다.

## 테스트

```bash
./run.sh test
```

```
Ran 45 tests in 0.007s
OK
```

TTL 테스트에서 실제로 기다리지 않는 이유는 `Store` 가 시계 함수를 주입받도록
만들었기 때문입니다. 테스트는 가짜 시계를 넣고 시간을 돌려버립니다.

## 제약 사항 준수

| 요구 | 지킨 방법 |
|---|---|
| `dict`·`set`·`collections` 금지 | `HashMap`·`MinHeap`·`DoublyLinkedList` 직접 구현 |
| 자료구조는 독립 모듈로 분리 | 파일 단위로 분리 (위 구조 참고) |
| 해시 함수 직접 설계 | FNV-1a 방식 (`hash_map.py`) |
| 로드 팩터 0.75 초과 시 2배 확장 | `_resize()` |
| 모든 리스트 연산 O(1) | 보초 노드를 둔 이중 연결 리스트 |
| 네트워크·영속성·동시성 미구현 | CLI 전용, 메모리에만 저장 |

파이썬 `list` 는 "고정 길이 배열 + 인덱스 접근" 수준으로만 사용했고
(`[None] * capacity` 생성 후 `arr[i]` 접근), 확장 로직은 직접 구현했습니다.

### 제약 준수를 기계로 검증하기

```bash
./run.sh check
```

```
검사 대상: miniredis/ 의 파이썬 파일 14개
금지 항목: dict, set, frozenset, collections, {} 리터럴/컴프리헨션
  위반 없음
✅ dict / set / collections 를 전혀 사용하지 않았습니다.
```

`grep` 으로는 정확히 검사할 수 없습니다. `self.store.set(...)` 은 직접 만든
메서드 호출이지 내장 `set()` 이 아닌데, 문자열 검색은 둘을 구분하지 못하기
때문입니다. 그래서 `tools/check_constraints.py` 는 파이썬 `ast` 모듈로
**구문 트리를 읽어서** 이름 노드(`Name`)와 속성 노드(`Attribute`)를 구분합니다.
