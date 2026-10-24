import unittest

from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.tokens import JavelinError


def parse(source):
    return Parser(Lexer(source).scan()).parse()


class FrontendTests(unittest.TestCase):
    def test_variable_and_output(self):
        program = parse(
            'let x = 10\nsay x\n'
        )
        self.assertEqual(len(program.statements), 2)

    def test_operator_precedence(self):
        program = parse('let x = 2 + 3 * 4\n')
        self.assertEqual(len(program.statements), 1)

    def test_function_definition_and_call(self):
        program = parse(
            'fn double(x) { give x * 2 }\n'
            'let y = run double(21)\n'
        )
        self.assertEqual(len(program.statements), 2)

    def test_reject_return_outside_function(self):
        with self.assertRaises(JavelinError):
            parse('give 42\n')

    def test_reject_invalid_character(self):
        with self.assertRaises(JavelinError):
            Lexer('let x = @').scan()

    def test_semicolon_separator(self):
        program = parse('let x = 1; let y = 2')
        self.assertEqual(len(program.statements), 2)


if __name__ == '__main__':
    unittest.main()