from dataclasses import dataclass
from typing import Any

from compiler.ast_nodes import *


class JavelinRuntimeError(Exception):
    """An error while executing a Javelin program."""


@dataclass
class Variable:
    value: Any
    mutable: bool


@dataclass
class UserFunction:
    parameters: list[str]
    body: Any
    closure: dict[str, Variable]


class _StopSignal(Exception):
    pass


class _ReturnSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


class Interpreter:
    def __init__(self, input_fn=input, output_fn=print):
        self.globals: dict[str, Variable] = {}
        self.scopes: list[dict[str, Variable]] = [self.globals]
        self.functions: dict[str, UserFunction] = {}
        self.input_fn = input_fn
        self.output_fn = output_fn
        self.loop_depth = 0
        self.call_depth = 0
        self.max_call_depth = 128
        self.max_loop_iterations = 1_000_000

    def run(self, program):
        try:
            self._execute_statements(self._get(program, "statements", "body"))
        except _StopSignal:
            pass

    # ---------- AST compatibility helpers ----------

    @staticmethod
    def _get(node, *names, default=...):
        for name in names:
            if hasattr(node, name):
                return getattr(node, name)
        if default is not ...:
            return default
        raise JavelinRuntimeError(
            f"Internal AST error: {type(node).__name__} "
            f"is missing expected field {names[0]!r}."
        )

    @staticmethod
    def _kind(node):
        return type(node).__name__.lower()

    def _statements(self, block):
        return self._get(block, "statements", "body")

    # ---------- Scope and variables ----------

    def _find_variable(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise JavelinRuntimeError(f"Undefined variable: {name}")

    def _declare(self, name, value, mutable):
        if not isinstance(name, str):
            name = str(name)

        scope = self.scopes[-1]
        if name in scope:
            raise JavelinRuntimeError(
                f"Variable already declared in this scope: {name}"
            )
        if name in self.functions:
            raise JavelinRuntimeError(
                f"Name is already used by a function: {name}"
            )

        scope[name] = Variable(value=value, mutable=mutable)

    def _assign(self, name, value):
        variable = self._find_variable(name)
        if not variable.mutable:
            raise JavelinRuntimeError(
                f"Cannot change constant '{name}'."
            )
        variable.value = value

    # ---------- Statements ----------

    def _execute_statements(self, statements):
        for statement in statements:
            self._execute(statement)

    def _execute_block(self, block, new_scope=True):
        if new_scope:
            self.scopes.append({})
        try:
            self._execute_statements(self._statements(block))
        finally:
            if new_scope:
                self.scopes.pop()

    def _execute(self, node):
        kind = self._kind(node)

        if kind in ("declaration", "declare"):
            name = self._get(node, "name", "identifier")
            value = self._evaluate(self._get(node, "value", "expression"))
            mutable = self._get(
                node, "mutable", "is_mutable",
                default=not self._get(
                    node, "constant", "is_constant", default=False
                )
            )
            self._declare(name, value, bool(mutable))
            return

        if kind in ("assignment", "set"):
            name = self._get(node, "name", "identifier")
            value = self._evaluate(self._get(node, "value", "expression"))
            self._assign(name, value)
            return

        if kind in ("output", "say", "print"):
            value = self._evaluate(self._get(node, "value", "expression"))
            self.output_fn(self._format(value))
            return

        if kind in ("input", "ask"):
            name = self._get(node, "name", "identifier")
            variable = self._find_variable(name)
            if not variable.mutable:
                raise JavelinRuntimeError(
                    f"Cannot read input into constant '{name}'."
                )
            prompt = self._get(node, "prompt", default="")
            text = self.input_fn(str(prompt))
            variable.value = text
            return

        if kind in ("conditional", "ifstatement", "ifnode"):
            condition = self._evaluate(
                self._get(node, "condition", "test")
            )
            then_block = self._get(
                node, "then_block", "then_branch", "body"
            )
            else_block = self._get(
                node, "else_block", "else_branch", default=None
            )

            if self._truthy(condition):
                self._execute_block(then_block)
            elif else_block is not None:
                self._execute_block(else_block)
            return

        if kind in ("loop", "repeat", "loopstatement"):
            count = self._evaluate(
                self._get(node, "count", "iterations", "expression")
            )
            if isinstance(count, bool) or not isinstance(count, int):
                raise JavelinRuntimeError(
                    "'loop' requires an integer count."
                )
            if count < 0:
                raise JavelinRuntimeError(
                    "'loop' count cannot be negative."
                )
            if count > self.max_loop_iterations:
                raise JavelinRuntimeError(
                    f"Loop count exceeds limit ({self.max_loop_iterations})."
                )

            body = self._get(node, "body", "block")
            self.loop_depth += 1
            try:
                for _ in range(count):
                    try:
                        self._execute_block(body)
                    except _StopSignal:
                        break
            finally:
                self.loop_depth -= 1
            return

        if kind in ("function", "functiondefinition", "fn"):
            name = self._get(node, "name", "identifier")
            params = self._get(
                node, "parameters", "params", "arguments", default=[]
            )
            body = self._get(node, "body", "block")
            if name in self.functions:
                raise JavelinRuntimeError(
                    f"Function already defined: {name}"
                )
            self.functions[name] = UserFunction(
                parameters=list(params),
                body=body,
                closure=dict(self.scopes[0]),
            )
            return

        if kind in ("return", "returnstatement", "give"):
            value_node = self._get(
                node, "value", "expression", default=None
            )
            value = None if value_node is None else self._evaluate(value_node)
            raise _ReturnSignal(value)

        if kind in ("stop", "breakstatement"):
            if self.loop_depth:
                raise _StopSignal()
            raise _StopSignal()

        if kind in ("import", "importstatement"):
            raise JavelinRuntimeError(
                "Imports are parsed but are not implemented in v0.1."
            )

        raise JavelinRuntimeError(
            f"Unsupported statement: {type(node).__name__}"
        )

    # ---------- Expressions ----------

    def _evaluate(self, node):
        kind = self._kind(node)

        if kind in ("literal", "literalexpression"):
            return self._get(node, "value")

        if kind in ("name", "nameexpression", "identifier"):
            name = self._get(node, "name", "identifier", "value")
            if name == "true":
                return True
            if name == "false":
                return False
            return self._find_variable(name).value

        if kind in ("unary", "unaryexpression"):
            operator = self._get(node, "operator", "op")
            value = self._evaluate(
                self._get(node, "operand", "value", "expression")
            )
            if operator in ("-", "MINUS"):
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise JavelinRuntimeError("Unary '-' requires a number.")
                return -value
            if operator in ("!", "not", "NOT"):
                return not self._truthy(value)
            raise JavelinRuntimeError(f"Unknown unary operator: {operator}")

        if kind in ("binary", "binaryexpression"):
            left = self._evaluate(self._get(node, "left"))
            operator = self._get(node, "operator", "op")
            right_node = self._get(node, "right")

            # Short-circuit Boolean operators.
            if operator in ("and", "AND", "&&"):
                return self._truthy(left) and self._truthy(
                    self._evaluate(right_node)
                )
            if operator in ("or", "OR", "||"):
                return self._truthy(left) or self._truthy(
                    self._evaluate(right_node)
                )

            right = self._evaluate(right_node)
            return self._binary(operator, left, right)

        if kind in ("call", "callexpression", "functioncall"):
            name = self._get(node, "name", "function_name", "identifier")
            args = self._get(node, "arguments", "args", default=[])
            values = [self._evaluate(arg) for arg in args]
            return self._call(name, values)

        raise JavelinRuntimeError(
            f"Unsupported expression: {type(node).__name__}"
        )

    def _call(self, name, values):
        if name not in self.functions:
            raise JavelinRuntimeError(f"Undefined function: {name}")

        function = self.functions[name]
        if len(values) != len(function.parameters):
            raise JavelinRuntimeError(
                f"Function '{name}' expects {len(function.parameters)} "
                f"argument(s), got {len(values)}."
            )

        if self.call_depth >= self.max_call_depth:
            raise JavelinRuntimeError("Maximum function call depth exceeded.")

        local_scope = {
            parameter: Variable(value, mutable=True)
            for parameter, value in zip(function.parameters, values)
        }

        self.scopes.append(local_scope)
        self.call_depth += 1
        try:
            try:
                self._execute_block(function.body, new_scope=False)
            except _ReturnSignal as signal:
                return signal.value
            return None
        finally:
            self.call_depth -= 1
            self.scopes.pop()

    # ---------- Operators and values ----------

    def _binary(self, operator, left, right):
        if operator in ("+", "PLUS"):
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if self._is_number(left) and self._is_number(right):
                return left + right
            raise JavelinRuntimeError(
                "'+' requires two numbers or two strings."
            )

        if operator in ("-", "MINUS", "*", "STAR", "/", "SLASH", "%", "PERCENT"):
            if not self._is_number(left) or not self._is_number(right):
                raise JavelinRuntimeError(
                    f"'{operator}' requires numeric operands."
                )
            if operator in ("/", "SLASH", "%", "PERCENT") and right == 0:
                raise JavelinRuntimeError("Division by zero.")
            if operator in ("-", "MINUS"):
                return left - right
            if operator in ("*", "STAR"):
                return left * right
            if operator in ("/", "SLASH"):
                return left / right
            return left % right

        if operator in ("==", "EQEQ"):
            return type(left) is type(right) and left == right
        if operator in ("!=", "NE"):
            return not (type(left) is type(right) and left == right)

        if operator in ("<", "LT", "<=", "LE", ">", "GT", ">=", "GE"):
            if type(left) is not type(right) or not (
                self._is_number(left) or isinstance(left, str)
            ):
                raise JavelinRuntimeError(
                    "Comparison requires matching numbers or strings."
                )
            if operator in ("<", "LT"):
                return left < right
            if operator in ("<=", "LE"):
                return left <= right
            if operator in (">", "GT"):
                return left > right
            return left >= right

        raise JavelinRuntimeError(f"Unknown binary operator: {operator}")

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @staticmethod
    def _truthy(value):
        return bool(value)

    @staticmethod
    def _format(value):
        if value is True:
            return "true"
        if value is False:
            return "false"
        if value is None:
            return "null"
        return str(value)