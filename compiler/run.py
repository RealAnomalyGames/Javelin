from pathlib import Path
import sys

from compiler.interpreter import Interpreter, JavelinRuntimeError
from compiler.lexer import Lexer
from compiler.parser import Parser


ROOT = Path(__file__).resolve().parent.parent
ENTRY_FILE = ROOT / "input" / "main.jve"


def main():
    if not ENTRY_FILE.is_file():
        print(f"Javelin error: entry file not found: {ENTRY_FILE}")
        return 1

    try:
        source = ENTRY_FILE.read_text(encoding="utf-8")
        tokens = Lexer(source, filename=str(ENTRY_FILE)).scan()
        program = Parser(tokens).parse()
        
        Interpreter().run(program)
        return 0
    except (JavelinRuntimeError, SyntaxError, ValueError) as error:
        print(f"Javelin error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())