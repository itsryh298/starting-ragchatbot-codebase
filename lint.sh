#!/bin/bash
# Run linting checks

echo "Running flake8..."
cd backend && uv run flake8 .

echo "Running mypy..."
uv run mypy .

echo "Linting complete!"
