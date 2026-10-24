from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    EOF = auto()
    NEWLINE = auto()

    IDENT = auto()
    INTEGER = auto()
    STRING = auto()

    USE = auto()
    LET = auto()
    FIX = auto()
    SET = auto()
    SAY = auto()
    ASK = auto()
    IF = auto()
    ELSE = auto()
    LOOP = auto()
    STOP = auto()
    FN = auto()
    RUN = auto()
    GIVE = auto()
    TRUE = auto()
    FALSE = auto()

    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()

    BANG = auto()
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    BANG_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    AND_AND = auto()
    OR_OR = auto()


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    lexeme: str
    value: object
    line: int
    column: int

    def __str__(self):
        return (
            f"{self.kind.name}({self.lexeme!r}) "
            f"at {self.line}:{self.column}"
        )


class JavelinError(Exception):
    def __init__(self, message, line, column, filename="<source>"):
        self.message = message
        self.line = line
        self.column = column
        self.filename = filename

        super().__init__(
            f"{filename}:{line}:{column}: {message}"
        )