@echo off
REM Run all code quality checks

echo === Code Quality Checks ===
echo.

echo 1. Checking import order with isort...
cd backend
uv run isort . --check-only --diff
set ISORT_EXIT=%ERRORLEVEL%

echo.
echo 2. Checking code formatting with black...
uv run black . --check --diff
set BLACK_EXIT=%ERRORLEVEL%

echo.
echo 3. Running flake8 linter...
uv run flake8 .
set FLAKE8_EXIT=%ERRORLEVEL%

echo.
echo === Summary ===
if %ISORT_EXIT%==0 if %BLACK_EXIT%==0 if %FLAKE8_EXIT%==0 (
    echo √ All quality checks passed!
    echo.
    echo Note: Run 'cd backend && uv run mypy .' separately for type checking (optional^)
    exit /b 0
) else (
    echo × Some quality checks failed. Run format.bat to auto-fix formatting issues.
    exit /b 1
)
