from .tokens import Token, TokenKind as K, JavelinError


KEYWORDS = {
    "use": K.USE,
    "let": K.LET,
    "fix": K.FIX,
    "set": K.SET,
    "say": K.SAY,
    "ask": K.ASK,
    "if": K.IF,
    "else": K.ELSE,
    "loop": K.LOOP,
    "stop": K.STOP,
    "fn": K.FN,
    "run": K.RUN,
    "give": K.GIVE,
    "true": K.TRUE,
    "false": K.FALSE,
}

TWO_CHAR = {
    "==": K.EQUAL_EQUAL,
    "!=": K.BANG_EQUAL,
    "<=": K.LESS_EQUAL,
    ">=": K.GREATER_EQUAL,
    "&&": K.AND_AND,
    "||": K.OR_OR,
}

ONE_CHAR = {
    "(": K.LPAREN,
    ")": K.RPAREN,
    "{": K.LBRACE,
    "}": K.RBRACE,
    ",": K.COMMA,
    ":": K.COLON,
    ";": K.SEMICOLON,
    "+": K.PLUS,
    "-": K.MINUS,
    "*": K.STAR,
    "/": K.SLASH,
    "%": K.PERCENT,
    "!": K.BANG,
    "=": K.EQUAL,
    "<": K.LESS,
    ">": K.GREATER,
}


class Lexer:
    def __init__(self, source, filename="<source>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.paren_depth = 0

    def scan(self):
        while not self._at_end():
            ch = self._peek()

            if ch in " \t\r":
                self._advance()
            elif ch == "\n":
                line, col = self.line, self.column
                self._advance()
                if self.paren_depth == 0:
                    self._emit(K.NEWLINE, "\n", None, line, col)
            elif ch == "#":
                self._comment()
            elif ch == '"':
                self._string()
            elif ch.isascii() and ch.isdigit():
                self._number()
            elif ch.isascii() and (
                ch.isalpha() or ch == "_"
            ):
                self._identifier()
            else:
                pair = ch + self._peek_next()

                if pair in TWO_CHAR:
                    line, col = self.line, self.column
                    self._advance()
                    self._advance()
                    self._emit(
                        TWO_CHAR[pair], pair, None, line, col
                    )
                elif ch in ONE_CHAR:
                    line, col = self.line, self.column
                    self._advance()
                    kind = ONE_CHAR[ch]

                    if kind == K.LPAREN:
                        self.paren_depth += 1
                    elif kind == K.RPAREN:
                        self.paren_depth -= 1
                        if self.paren_depth < 0:
                            self._error(
                                "Unmatched ')'", line, col
                            )

                    self._emit(kind, ch, None, line, col)
                else:
                    self._error(
                        f"Unexpected character {ch!r}"
                    )

        if self.paren_depth != 0:
            self._error("Unclosed '('")

        self._emit(
            K.EOF, "", None, self.line, self.column
        )
        return self.tokens

    def _peek(self):
        if self._at_end():
            return "\0"
        return self.source[self.pos]

    def _peek_next(self):
        if self.pos + 1 >= len(self.source):
            return "\0"
        return self.source[self.pos + 1]

    def _advance(self):
        ch = self.source[self.pos]
        self.pos += 1

        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return ch

    def _at_end(self):
        return self.pos >= len(self.source)

    def _emit(self, kind, lexeme, value, line, column):
        self.tokens.append(
            Token(kind, lexeme, value, line, column)
        )

    def _error(self, message, line=None, column=None):
        raise JavelinError(
            message,
            line or self.line,
            column or self.column,
            self.filename,
        )

    def _comment(self):
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _identifier(self):
        start = self.pos
        line, col = self.line, self.column

        while True:
            ch = self._peek()
            if ch.isascii() and (
                ch.isalnum() or ch == "_"
            ):
                self._advance()
            else:
                break

        text = self.source[start:self.pos]
        kind = KEYWORDS.get(text, K.IDENT)

        value = None
        if kind == K.TRUE:
            value = True
        elif kind == K.FALSE:
            value = False

        self._emit(kind, text, value, line, col)

    def _number(self):
        start = self.pos
        line, col = self.line, self.column

        while self._peek().isascii() and self._peek().isdigit():
            self._advance()

        text = self.source[start:self.pos]
        value = int(text)

        if value > 32768:
            self._error(
                "Integer literal exceeds the v0.1 limit",
                line,
                col,
            )

        self._emit(K.INTEGER, text, value, line, col)

    
    def _string(self):
        start = self.pos
        line, col = self.line, self.column
        self._advance()  # Opening quote
        chars = []

        escapes = {
            "n": "\n",
            "r": "\r",
            "t": "\t",
            '"': '"',
            "\\": "\\",
        }

        while not self._at_end():
            ch = self._advance()

            if ch == '"':
                self._emit(
                    K.STRING,
                    self.source[start:self.pos],
                    "".join(chars),
                    line,
                    col,
                )
                return

            if ch == "\n":
                self._error(
                    "Unterminated string literal", line, col
                )

            if ch == "\\":
                if self._at_end():
                    self._error(
                        "Unterminated escape sequence", line, col
                    )

                escaped = self._advance()
                if escaped not in escapes:
                    self._error(
                        f"Invalid escape sequence '\\{escaped}'",
                        self.line,
                        self.column - 2,
                    )
                chars.append(escapes[escaped])
            else:
                chars.append(ch)

        self._error("Unterminated string literal", line, col)