
from .tokens import TokenKind as K, JavelinError
from . import ast_nodes as A


class Parser:
    def __init__(self, tokens, filename="<source>"):
        self.tokens = tokens
        self.filename = filename
        self.pos = 0
        self.function_depth = 0

    def parse(self):
        statements = []
        self._separators()

        while not self._check(K.EOF):
            statements.append(self._statement())
            if not self._check(K.EOF):
                if not self._check(K.RBRACE):
                    if not self._check(K.NEWLINE) and not self._check(K.SEMICOLON):
                        self._error("Expected a statement separator")
                self._separators()

        return A.Program(statements)

    def _statement(self):
        if self._match(K.USE):
            path = self._consume(K.STRING, "Expected module path")
            return A.Import(path.value)

        if self._match(K.LET, K.FIX):
            immutable = self._previous().kind == K.FIX
            name = self._consume(K.IDENT, "Expected variable name")
            type_name = None

            if self._match(K.COLON):
                type_name = self._consume(
                    K.IDENT, "Expected type name"
                ).lexeme

            self._consume(K.EQUAL, "Expected '='")
            return A.Declaration(
                name.lexeme, self._expression(),
                immutable, type_name
            )

        if self._match(K.SET):
            name = self._consume(K.IDENT, "Expected variable name")
            self._consume(K.EQUAL, "Expected '='")
            return A.Assignment(name.lexeme, self._expression())

        if self._match(K.SAY):
            return A.Output(self._expression())

        if self._match(K.ASK):
            name = self._consume(K.IDENT, "Expected variable name")
            return A.Input(name.lexeme)

        if self._match(K.IF):
            condition = self._expression()
            then_block = self._block()
            else_branch = None

            if self._match(K.ELSE):
                if self._match(K.IF):
                    nested_condition = self._expression()
                    nested_block = self._block()
                    nested_else = None
                    if self._match(K.ELSE):
                        nested_else = self._block()
                    else_branch = A.Conditional(
                        nested_condition, nested_block, nested_else
                    )
                else:
                    else_branch = self._block()

            return A.Conditional(
                condition, then_block, else_branch
            )

        if self._match(K.LOOP):
            count = self._expression()
            return A.Loop(count, self._block())

        if self._match(K.FN):
            name = self._consume(K.IDENT, "Expected function name")
            self._consume(K.LPAREN, "Expected '('")
            params = []

            if not self._check(K.RPAREN):
                params.append(
                    self._consume(K.IDENT, "Expected parameter").lexeme
                )
                while self._match(K.COMMA):
                    params.append(
                        self._consume(
                            K.IDENT, "Expected parameter"
                        ).lexeme
                    )

            self._consume(K.RPAREN, "Expected ')'")
            if len(set(params)) != len(params):
                self._error("Duplicate function parameter")

            self.function_depth += 1
            try:
                body = self._block()
            finally:
                self.function_depth -= 1

            return A.Function(name.lexeme, params, body)

        if self._match(K.GIVE):
            if self.function_depth == 0:
                self._error("'give' is only valid inside a function")

            value = None
            if not self._is_separator() and not self._check(K.RBRACE) and not self._check(K.EOF):
                value = self._expression()

            return A.Return(value)

        if self._match(K.STOP):
            return A.Stop()

        return self._expression()

    def _block(self):
        self._consume(K.LBRACE, "Expected '{'")
        statements = []
        self._separators()

        while not self._check(K.RBRACE) and not self._check(K.EOF):
            statements.append(self._statement())

            if not self._check(K.RBRACE) and not self._is_separator():
                self._error("Expected a statement separator")

            self._separators()

        self._consume(K.RBRACE, "Expected '}'")
        return A.Block(statements)

    def _expression(self):
        return self._logical_or()

    def _logical_or(self):
        expr = self._logical_and()
        while self._match(K.OR_OR):
            op = self._previous().lexeme
            expr = A.Binary(expr, op, self._logical_and())
        return expr

    def _logical_and(self):
        expr = self._equality()
        while self._match(K.AND_AND):
            op = self._previous().lexeme
            expr = A.Binary(expr, op, self._equality())
        return expr

    def _equality(self):
        expr = self._comparison()
        while self._match(K.EQUAL_EQUAL, K.BANG_EQUAL):
            op = self._previous().lexeme
            expr = A.Binary(expr, op, self._comparison())
        return expr

    def _comparison(self):
        expr = self._additive()
        while self._match(
            K.LESS, K.LESS_EQUAL, K.GREATER, K.GREATER_EQUAL
        ):
            op = self._previous().lexeme
            expr = A.Binary(expr, op, self._additive())
        return expr

    def _additive(self):
        expr = self._multiplicative()
        while self._match(K.PLUS, K.MINUS):
            op = self._previous().lexeme
            expr = A.Binary(expr, op, self._multiplicative())
        return expr

    def _multiplicative(self):
        expr = self._unary()
        while self._match(K.STAR, K.SLASH, K.PERCENT):
            op = self._previous().lexeme
            expr = A.Binary(expr, op, self._unary())
        return expr

    def _unary(self):
        if self._match(K.BANG, K.MINUS, K.PLUS):
            op = self._previous().lexeme
            return A.Unary(op, self._unary())
        return self._postfix()

    def _postfix(self):
        expr = self._primary()

        # Function invocation must be written as:
        # run functionName(arguments)
        return expr

    def _primary(self):
        if self._match(K.INTEGER, K.STRING):
            return A.Literal(self._previous().value)

        if self._match(K.TRUE):
            return A.Literal(True)

        if self._match(K.FALSE):
            return A.Literal(False)

        if self._match(K.IDENT):
            return A.Name(self._previous().lexeme)

        if self._match(K.RUN):
            name = self._consume(K.IDENT, "Expected function name")
            self._consume(K.LPAREN, "Expected '('")
            args = []

            if not self._check(K.RPAREN):
                args.append(self._expression())
                while self._match(K.COMMA):
                    args.append(self._expression())

            self._consume(K.RPAREN, "Expected ')'")
            return A.Call(name.lexeme, args)

        if self._match(K.LPAREN):
            expr = self._expression()
            self._consume(K.RPAREN, "Expected ')'")
            return expr

        self._error("Expected an expression")

    def _separators(self):
        while self._match(K.NEWLINE, K.SEMICOLON):
            pass

    def _is_separator(self):
        return self._check(K.NEWLINE) or self._check(K.SEMICOLON)

    def _check(self, kind):
        return self._peek().kind == kind

    def _match(self, *kinds):
        if self._peek().kind in kinds:
            self.pos += 1
            return True
        return False

    def _consume(self, kind, message):
        if self._check(kind):
            token = self._peek()
            self.pos += 1
            return token
        self._error(message)

    def _peek(self):
        return self.tokens[self.pos]

    def _previous(self):
        return self.tokens[self.pos - 1]

    def _error(self, message):
        token = self._peek()
        raise JavelinError(
            message, token.line, token.column, self.filename
        )
