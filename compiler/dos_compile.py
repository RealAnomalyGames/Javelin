from pathlib import Path
import sys

from compiler.dos_codegen import DOSCodeGenerator, DOSCodegenError
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.tokens import JavelinError


ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "input" / "main.jve"
OUTPUT_FILE = ROOT / "output" / "main.exe"


def main():
    if not INPUT_FILE.is_file():
        print(f"Javelin error: entry file not found: {INPUT_FILE}")
        return 1

    try:
        source = INPUT_FILE.read_text(encoding="utf-8")
        tokens = Lexer(source, filename=str(INPUT_FILE)).scan()
        program = Parser(tokens, filename=str(INPUT_FILE)).parse()

        result = DOSCodeGenerator().compile(program, OUTPUT_FILE)

        print(f"Created DOS executable: {result.relative_to(ROOT)}")
        print("Target: 16-bit MS-DOS MZ executable")
        print("Integer range: -32768 through 32767")
        print("Output: ASCII string literals")
        print("Note: unsupported features produce compilation errors.")
        return 0

    except (DOSCodegenError, JavelinError, SyntaxError, ValueError) as error:
        print(f"Javelin DOS compilation error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())