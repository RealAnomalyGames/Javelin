# Javelin 0.1.0 — Public Beta

**Javelin** is an experimental general-purpose programming language with `.jve` source files and a compiler that can generate 16-bit DOS MZ executables.

Javelin 0.1.0 is the project's first public beta release. It is an early-stage project intended for experimentation, testing, and continued development.

> **Status:** Public beta  
> **Version:** 0.1.0  
> **Source extension:** `.jve`  
> **Executable target:** 16-bit MS-DOS  
> **Build environment:** Windows, Python, and PowerShell

## Features

Javelin 0.1.0 includes:

- A lexer and parser for Javelin source code.
- An interpreter for supported language constructs.
- Variables and immutable constants.
- Arithmetic and Boolean expressions.
- Comparisons and logical operators.
- Conditional statements with `if` and `else`.
- Counted loops.
- Functions and return statements in the interpreter.
- Text and integer output in the DOS backend.
- A DOS executable generator targeting 16-bit MZ executables.
- A PowerShell build workflow with Python unit tests.
- A batch-file entry point for convenient building on Windows.

**Important:** The interpreter and DOS compiler do not support exactly the same feature set. Some language features, including imports, keyboard input, and function calls, are not currently implemented in the DOS backend.

## Getting started

### Requirements

To build Javelin from source, you need:

- Windows with Windows PowerShell.
- Python installed and available as `python` on your PATH.
- The Javelin source code.
- MS-DOS 6.22 in VirtualBox, or another suitable DOS environment, to run and test the generated executable.

A modern 64-bit Windows installation generally cannot execute a 16-bit DOS program directly. Run the generated executable inside a compatible DOS environment.

### Build Javelin

1. Open or extract the Javelin project directory.
2. Make sure `input/main.jve` contains your Javelin program.
3. Run `compile-DOS.bat`.

The build workflow runs the Python unit tests and invokes the DOS compiler. If the tests pass and compilation succeeds, the generated executable is written to:

```text
output/main.exe
```

To run the PowerShell workflow directly, open PowerShell in the project directory and run:

```powershell
.\build-Javelin.ps1
```

To skip the unit tests and compile directly:

```powershell
.\build-Javelin.ps1 -SkipTests
```

Skipping tests is useful for quick iteration, but running the full build is recommended before publishing a release.

## Your first Javelin program

Create a file named `input/main.jve` containing:

```javelin
say "Hello, world!"

let score = 10
set score = score + 5

say "Updated score:"
say score

if score > 10 {
    say "The score is greater than 10."
} else {
    say "The score is 10 or less."
}

loop 3 {
    say "Javelin is running!"
}

stop
```

Build the program with `compile-DOS.bat`. Transfer `output/main.exe` to your DOS environment and run:

```dos
MAIN.EXE
```

## Language overview

### Variables and constants

```javelin
let score = 10
set score = score + 5

fix maximum = 100
```

`let` declares a mutable variable. `fix` declares an immutable value. `set` assigns a new value to an existing mutable variable.

Explicit type annotations are not currently supported by the DOS backend.

### Output

```javelin
say "Hello from Javelin!"
say 42
say -123
say 10 + 5
```

The DOS backend supports ASCII string output and signed 16-bit integer output. Integer values must fit within the range `-32768` through `32767`.

### Conditions

```javelin
if score >= 15 {
    say "Target reached."
} else {
    say "Keep going."
}
```

### Loops

```javelin
loop 3 {
    say "Repeated output"
}
```

The DOS backend currently requires a literal integer loop count.

### Expressions

The frontend and DOS backend include support for arithmetic, comparisons, logical operators, and unary operators. DOS arithmetic uses 16-bit integer values; floating-point arithmetic is not supported by the DOS output formatter.

## Current limitations

Javelin 0.1.0 is an early beta. Known limitations include:

- The DOS compiler supports a subset of the full language.
- Imports are not implemented.
- Keyboard input using `ask` is not implemented in the DOS backend.
- Function definitions and function calls are not implemented in the DOS backend.
- Explicit type annotations are not supported by the DOS backend.
- DOS numeric output supports signed 16-bit integers, not floating-point values.
- The DOS target requires a compatible DOS environment to execute.

The project may contain additional bugs or unsupported edge cases. Successful tests do not guarantee compatibility with every possible program.

## Project structure

```text
Javelin/
├── compiler/
│   ├── tokens.py
│   ├── lexer.py
│   ├── ast_nodes.py
│   ├── parser.py
│   ├── check.py
│   ├── interpreter.py
│   ├── run.py
│   ├── dos_codegen.py
│   └── dos_compile.py
├── input/
│   └── main.jve
├── output/
│   └── main.exe
├── tests/
│   ├── test_frontend.py
│   └── test_interpreter.py
├── build-Javelin.ps1
├── compile-DOS.bat
└── run-Javelin.bat
```

## Testing

Run the complete Python test suite with:

```powershell
python -m unittest discover -s tests -v
```

Build and test the generated executable separately in a DOS environment. The Python tests validate the tested frontend and interpreter behavior; they do not replace testing the generated DOS executable.

## Reporting bugs and requesting features

When reporting a bug, include:

1. Your Javelin version.
2. Your operating system and Python version.
3. The smallest `.jve` program that reproduces the problem.
4. The command you ran.
5. The complete error message or unexpected DOS output.

Please distinguish between a problem in the interpreter and a problem in the DOS compiler where possible.

## Release history

### 0.1.0 — First public beta

- Initial public beta release.
- Javelin lexer, parser, and interpreter.
- Initial 16-bit DOS MZ executable generation.
- Windows batch and PowerShell build workflow.
- Initial Python test suite.

## A note about the beta

Javelin is under active development. Language syntax, compiler behavior, and project structure may change in future releases. Back up your source files and keep copies of released versions when experimenting with the beta.