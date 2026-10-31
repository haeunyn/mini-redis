"""명령어 한 줄을 토큰으로 쪼갠다.

큰따옴표로 감싼 값 안의 공백은 하나의 토큰으로 유지한다.
    SET user:1 "Alice Kim"  ->  ['SET', 'user:1', 'Alice Kim']

shlex 같은 표준 모듈을 쓰지 않고 직접 짠 이유:
    상태(지금 따옴표 안인가?)를 들고 글자를 하나씩 훑는 가장 기본적인
    파싱 방식을 눈으로 보여주기 위해서다. 규칙이 단순해서 20줄이면 된다.
"""


def tokenize(line: str):
    """한 줄을 토큰 리스트로 만든다."""
    tokens = []
    buf = []            # 지금 만들고 있는 토큰의 글자들
    in_quotes = False   # 지금 큰따옴표 안인가?

    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes       # 따옴표는 상태만 뒤집고 버린다
        elif ch.isspace() and not in_quotes:
            if buf:                          # 따옴표 밖의 공백 = 토큰 경계
                tokens.append("".join(buf))
                buf = []
        else:
            buf.append(ch)

    if buf:
        tokens.append("".join(buf))
    return tokens


def parse_int(text: str) -> int:
    """정수로 바꾼다. 실패하면 ValueError 를 올린다.

    '12.5' 나 'abc' 처럼 정수가 아닌 입력을 걸러내기 위해 int() 를 그대로 쓴다.
    """
    return int(text)
