param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# Javelin PowerShell Build Workflow
# Target: 16-bit MS-DOS MZ executable
# ------------------------------------------------------------

$ProjectRoot = $PSScriptRoot
$SourceFile = Join-Path $ProjectRoot "input\main.jve"
$OutputFile = Join-Path $ProjectRoot "output\main.exe"
$TestsDirectory = Join-Path $ProjectRoot "tests"

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "       JAVELIN BUILD WORKFLOW         " -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify the project structure.
Write-Host "[1/4] Checking project files..."

if (-not (Test-Path $SourceFile -PathType Leaf)) {
    Write-Host "ERROR: Source file not found:" -ForegroundColor Red
    Write-Host "       $SourceFile"
    exit 1
}

$CompilerFile = Join-Path $ProjectRoot "compiler\dos_compile.py"

if (-not (Test-Path $CompilerFile -PathType Leaf)) {
    Write-Host "ERROR: DOS compiler not found:" -ForegroundColor Red
    Write-Host "       $CompilerFile"
    exit 1
}

Write-Host "Source file found." -ForegroundColor Green
Write-Host "DOS compiler found." -ForegroundColor Green

# Step 2: Find Python.
Write-Host ""
Write-Host "[2/4] Checking Python..."

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue

if (-not $PythonCommand) {
    Write-Host "ERROR: Python was not found in PATH." -ForegroundColor Red
    Write-Host "Install Python or add it to PATH, then try again."
    exit 1
}

& python --version

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python could not start." -ForegroundColor Red
    exit 1
}

# Step 3: Run tests unless skipped.
if ($SkipTests) {
    Write-Host ""
    Write-Host "[3/4] Skipping tests as requested." -ForegroundColor Yellow
}
else {
    Write-Host ""
    Write-Host "[3/4] Running Javelin tests..."

    if (-not (Test-Path $TestsDirectory -PathType Container)) {
        Write-Host "ERROR: Tests directory not found:" -ForegroundColor Red
        Write-Host "       $TestsDirectory"
        exit 1
    }

    Push-Location $ProjectRoot

    try {
        & python -m unittest discover -s tests -v

        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "ERROR: Tests failed. Build cancelled." -ForegroundColor Red
            exit 1
        }
    }
    finally {
        Pop-Location
    }

    Write-Host "All tests passed." -ForegroundColor Green
}

# Step 4: Compile the DOS executable.
Write-Host ""
Write-Host "[4/4] Compiling Javelin to DOS EXE..."

if (-not (Test-Path (Split-Path $OutputFile) -PathType Container)) {
    New-Item -ItemType Directory -Path (Split-Path $OutputFile) -Force |
        Out-Null
}

Push-Location $ProjectRoot

try {
    & python -m compiler.dos_compile

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERROR: DOS compilation failed." -ForegroundColor Red
        exit 1
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path $OutputFile -PathType Leaf)) {
    Write-Host "ERROR: Compiler reported success but no EXE was created." `
        -ForegroundColor Red
    exit 1
}

$Executable = Get-Item $OutputFile

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "          BUILD SUCCESSFUL            " -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Source:     $SourceFile"
Write-Host "Executable: $OutputFile"
Write-Host ("Size:       {0:N0} bytes" -f $Executable.Length)
Write-Host "Target:     16-bit DOS MZ"
Write-Host ""
Write-Host "Copy or transfer main.exe to your DOS 6.22 VM to test it."
Write-Host ""