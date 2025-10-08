# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Development

### Code Quality Tools

This project uses several code quality tools to maintain consistency and catch potential issues:

- **black**: Automatic code formatter (88 character line length)
- **isort**: Import statement organizer (compatible with black)
- **flake8**: Linter for style guide enforcement and error detection
- **mypy**: Static type checker for Python

#### Quick Commands

**Format code automatically:**
```bash
# Git Bash on Windows
./format.sh

# Windows CMD/PowerShell
format.bat
```

**Run linting checks:**
```bash
# Git Bash on Windows
./lint.sh

# Windows CMD/PowerShell
lint.bat
```

**Run all quality checks:**
```bash
# Git Bash on Windows
./quality-check.sh

# Windows CMD/PowerShell
quality-check.bat
```

#### Development Workflow

1. Make your code changes
2. Run `./format.sh` to auto-format your code
3. Run `./quality-check.sh` to verify all checks pass
4. Commit your changes

All quality tools are configured in:
- `pyproject.toml` - black, isort, and mypy configuration
- `.flake8` - flake8 configuration

