# RAG System Test Suite

This directory contains the test suite for the RAG (Retrieval-Augmented Generation) system.

## Test Structure

```
backend/tests/
├── __init__.py           # Test package initialization
├── conftest.py          # Shared pytest fixtures and mocks
├── test_api.py          # API endpoint tests
└── README.md            # This file
```

## Running Tests

### Run all tests
```bash
cd backend
uv run pytest
```

### Run specific test file
```bash
cd backend
uv run pytest tests/test_api.py
```

### Run with verbose output
```bash
cd backend
uv run pytest -v
```

### Run tests by marker
```bash
# Run only API tests
cd backend
uv run pytest -m api

# Run only unit tests
cd backend
uv run pytest -m unit

# Run only integration tests
cd backend
uv run pytest -m integration
```

### Run specific test class or function
```bash
# Run a specific test class
cd backend
uv run pytest tests/test_api.py::TestQueryEndpoint

# Run a specific test function
cd backend
uv run pytest tests/test_api.py::TestQueryEndpoint::test_query_with_session_id
```

## Test Categories

### API Tests (`test_api.py`)
Tests for FastAPI endpoints:
- **TestQueryEndpoint**: Tests for `/api/query` endpoint
  - Query with/without session ID
  - Response structure validation
  - Source formatting (string/dict)
  - Error handling
  - Edge cases (empty query, missing fields)

- **TestCoursesEndpoint**: Tests for `/api/courses` endpoint
  - Course statistics retrieval
  - Response structure validation
  - Empty catalog handling
  - Error handling

- **TestEndpointIntegration**: Integration tests
  - Multiple queries in same session
  - Query followed by course stats
  - CORS headers validation

## Available Fixtures

All fixtures are defined in `conftest.py`:

### Configuration
- `mock_config`: Mock configuration object with test settings

### Mock Components
- `mock_vector_store`: Mocked VectorStore for testing
- `mock_ai_generator`: Mocked AIGenerator for testing
- `mock_session_manager`: Mocked SessionManager for testing
- `mock_tool_manager`: Mocked ToolManager for testing
- `mock_document_processor`: Mocked DocumentProcessor for testing
- `mock_rag_system`: Fully mocked RAGSystem with all dependencies

### Sample Data
- `sample_lesson`: Sample Lesson object
- `sample_course`: Sample Course object
- `sample_course_chunk`: Sample CourseChunk object
- `sample_query_request`: Sample API query request payload
- `sample_query_response`: Sample API query response payload
- `sample_course_stats`: Sample course statistics payload

### Test Utilities
- `test_app`: FastAPI test application (without static file mounting)
- `client`: TestClient for making API requests
- `temp_test_file`: Temporary test file with sample course content

## Writing New Tests

### Example: Adding a new API test

```python
import pytest

@pytest.mark.api
def test_new_endpoint(client, mock_rag_system):
    """Test description"""
    # Arrange
    mock_rag_system.some_method.return_value = "expected_value"

    # Act
    response = client.get("/api/new-endpoint")

    # Assert
    assert response.status_code == 200
    assert response.json()["key"] == "expected_value"
```

### Example: Using fixtures

```python
def test_with_fixtures(sample_course, mock_vector_store):
    """Test using predefined fixtures"""
    # Use fixtures in your test
    assert sample_course.title == "Building RAG Applications"
    mock_vector_store.add_course_metadata(sample_course)
    mock_vector_store.add_course_metadata.assert_called_once()
```

## Test Design Principles

1. **Isolation**: Tests use mocked dependencies to avoid external dependencies
2. **Test App Pattern**: API tests use a separate test app without static file mounting
3. **Comprehensive Coverage**: Tests cover happy paths, edge cases, and error scenarios
4. **Clear Naming**: Test names describe what is being tested
5. **AAA Pattern**: Tests follow Arrange-Act-Assert structure

## Configuration

Test configuration is in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["backend/tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = ["-v", "--strict-markers", "--tb=short", "--disable-warnings"]
```

## Continuous Integration

To integrate with CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    cd backend
    uv sync
    uv run pytest --tb=short
```

## Coverage (Future Enhancement)

To add code coverage tracking:

```bash
# Install coverage
uv add pytest-cov

# Run tests with coverage
uv run pytest --cov=. --cov-report=html
```
