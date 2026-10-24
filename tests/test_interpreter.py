import unittest

from compiler.interpreter import Interpreter
from compiler.lexer import Lexer
from compiler.parser import Parser


def execute(source, inputs=None):
    output = []
    answers = iter(inputs or [])

    program = Parser(Lexer(source).scan()).parse()
    Interpreter(
        input_fn=lambda prompt="": next(answers),
        output_fn=output.append,
    ).run(program)

    return output


class InterpreterTests(unittest.TestCase):
    def test_arithmetic_and_precedence(self):
        self.assertEqual(
            execute("let x = 2 + 3 * 4\nsay x"),
            ["14"],
        )

    def test_constant_and_variable(self):
        self.assertEqual(
            execute("let x = 1\nset x = 5\nsay x"),
            ["5"],
        )

    def test_condition(self):
        self.assertEqual(
            execute('if 5 > 2 {\n say "yes"\n} else {\n say "no"\n}'),
            ["yes"],
        )

    def test_loop(self):
        self.assertEqual(
            execute("loop 3 {\n say 7\n}"),
            ["7", "7", "7"],
        )

    def test_function(self):
        self.assertEqual(
            execute(
                "fn double(x) {\n give x * 2\n}\n"
                "let answer = run double(21)\n"
                "say answer"
            ),
            ["42"],
        )

    def test_stop_inside_loop(self):
        self.assertEqual(
            execute(
                "loop 5 {\n"
                " say 1\n"
                " stop\n"
                " say 2\n"
                "}\n"
                'say "done"'
            ),
            ["1", "done"],
        )

    def test_input(self):
        self.assertEqual(
            execute("let name = \"\"\nask name\nsay name", ["Alex"]),
            ["Alex"],
        )


if __name__ == "__main__":
    unittest.main()