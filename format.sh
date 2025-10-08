#!/bin/bash
# Format code with isort and black

echo "Running isort..."
cd backend && uv run isort .

echo "Running black..."
uv run black .

echo "Code formatting complete!"
