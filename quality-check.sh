#!/bin/bash
# Run all code quality checks

echo "=== Code Quality Checks ==="
echo ""

echo "1. Checking import order with isort..."
cd backend && uv run isort . --check-only --diff
ISORT_EXIT=$?

echo ""
echo "2. Checking code formatting with black..."
uv run black . --check --diff
BLACK_EXIT=$?

echo ""
echo "3. Running flake8 linter..."
uv run flake8 .
FLAKE8_EXIT=$?

echo ""
echo "=== Summary ==="
if [ $ISORT_EXIT -eq 0 ] && [ $BLACK_EXIT -eq 0 ] && [ $FLAKE8_EXIT -eq 0 ]; then
    echo "✓ All quality checks passed!"
    echo ""
    echo "Note: Run 'cd backend && uv run mypy .' separately for type checking (optional)"
    exit 0
else
    echo "✗ Some quality checks failed. Run ./format.sh to auto-fix formatting issues."
    exit 1
fi
