
from pathlib import Path
import sys

from .lexer import Lexer
from .parser import Parser
from .tokens import JavelinError


ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "input"


def main():
    if not INPUT.is_dir():
        print(f"Error: missing input folder: {INPUT}")
        return 1

    main_script = INPUT / "main.jve"
    if not main_script.is_file():
        print("Error: input/main.jve is required.")
        return 1

    scripts = sorted(INPUT.glob("*.jve"))
    failed = False

    for path in scripts:
        try:
            source = path.read_text(encoding="utf-8-sig")
            tokens = Lexer(source, str(path.relative_to(ROOT))).scan()
            program = Parser(
                tokens, str(path.relative_to(ROOT))
            ).parse()

            print(
                f"OK: {path.relative_to(ROOT)} "
                f"({len(program.statements)} top-level statements)"
            )
        except (JavelinError, UnicodeError) as exc:
            print(f"ERROR: {exc}")
            failed = True

    if failed:
        return 1

    print(f"Frontend check passed: {len(scripts)} script(s).")
    print("Note: this checks syntax only; no executable was generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
