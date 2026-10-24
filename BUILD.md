# Building Javelin v0.1

## Requirements

- Python 3.10 or newer
- Visual Studio Code is recommended for editing

## Source layout

Place Javelin source files in the root `input/` folder.
The entry script `input/main.jve` is required.

## Check source syntax

Open PowerShell in the Javelin project root and run:

    .\compile-DOS.bat

This currently checks the syntax of all `.jve` files directly
inside `input/`. It does not generate a DOS executable.

## Current limitations

- DOS machine-code generation is not implemented.
- Semantic validation is incomplete.
- Module imports are parsed but not resolved.
- Only top-level `.jve` files are discovered.
- Asset processing and sprite/scene scripts are planned for later.