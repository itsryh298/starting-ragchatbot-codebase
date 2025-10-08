"""
Pytest configuration and shared fixtures for RAG system tests.

This module provides reusable fixtures for mocking components and setting up test data.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
import sys
import os

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import Course, Lesson, CourseChunk


@pytest.fixture
def mock_config():
    """Mock configuration object for testing"""
    config = Mock()
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.MAX_TOOL_ROUNDS = 2
    config.CHROMA_PATH = "./test_chroma_db"
    return config


@pytest.fixture
def sample_lesson() -> Lesson:
    """Create a sample lesson for testing"""
    return Lesson(
        number=1,
        title="Introduction to RAG Systems",
        link="https://example.com/lesson-1",
        content="This lesson covers the basics of Retrieval-Augmented Generation systems."
    )


@pytest.fixture
def sample_course(sample_lesson) -> Course:
    """Create a sample course for testing"""
    return Course(
        title="Building RAG Applications",
        instructor="Claude Code",
        course_link="https://example.com/course",
        lessons=[sample_lesson]
    )


@pytest.fixture
def sample_course_chunk(sample_course) -> CourseChunk:
    """Create a sample course chunk for testing"""
    return CourseChunk(
        course_title=sample_course.title,
        lesson_number=1,
        content="This lesson covers the basics of RAG systems.",
        chunk_index=0
    )


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore for testing"""
    mock = Mock()
    mock.search = Mock(return_value=Mock(
        documents=["Sample content about RAG systems"],
        metadatas=[{"course_title": "Building RAG Applications", "lesson_number": 1}],
        distances=[0.5]
    ))
    mock.add_course_metadata = Mock()
    mock.add_course_content = Mock()
    mock.get_course_count = Mock(return_value=1)
    mock.get_existing_course_titles = Mock(return_value=["Building RAG Applications"])
    mock.clear_all_data = Mock()
    return mock


@pytest.fixture
def mock_ai_generator():
    """Mock AIGenerator for testing"""
    mock = Mock()
    mock.generate_response = Mock(return_value="This is a test response about RAG systems.")
    return mock


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for testing"""
    mock = Mock()
    mock.create_session = Mock(return_value="session_1")
    mock.get_conversation_history = Mock(return_value=None)
    mock.add_exchange = Mock()
    return mock


@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager for testing"""
    mock = Mock()
    mock.get_tool_definitions = Mock(return_value=[
        {
            "name": "search_course_content",
            "description": "Search course content",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "course_name": {"type": "string"}
                }
            }
        }
    ])
    mock.get_last_sources = Mock(return_value=[
        {"text": "Building RAG Applications - Lesson 1", "link": "https://example.com/lesson-1"}
    ])
    mock.reset_sources = Mock()
    mock.register_tool = Mock()
    return mock


@pytest.fixture
def mock_document_processor():
    """Mock DocumentProcessor for testing"""
    mock = Mock()

    def mock_process(file_path):
        course = Course(
            title="Test Course",
            instructor="Test Instructor",
            course_link="https://example.com/course",
            lessons=[
                Lesson(
                    number=1,
                    title="Test Lesson",
                    link="https://example.com/lesson-1",
                    content="Test content"
                )
            ]
        )
        chunk = CourseChunk(
            course_title="Test Course",
            lesson_number=1,
            content="Test content",
            chunk_index=0
        )
        return course, [chunk]

    mock.process_course_document = Mock(side_effect=mock_process)
    return mock


@pytest.fixture
def sample_query_request() -> Dict[str, Any]:
    """Sample query request payload"""
    return {
        "query": "What is a RAG system?",
        "session_id": "session_1"
    }


@pytest.fixture
def sample_query_response() -> Dict[str, Any]:
    """Sample query response payload"""
    return {
        "answer": "A RAG system is a Retrieval-Augmented Generation system.",
        "sources": [
            {
                "text": "Building RAG Applications - Lesson 1",
                "link": "https://example.com/lesson-1"
            }
        ],
        "session_id": "session_1"
    }


@pytest.fixture
def sample_course_stats() -> Dict[str, Any]:
    """Sample course statistics payload"""
    return {
        "total_courses": 1,
        "course_titles": ["Building RAG Applications"]
    }


@pytest.fixture
def mock_rag_system(
    mock_vector_store,
    mock_ai_generator,
    mock_session_manager,
    mock_tool_manager,
    mock_document_processor
):
    """Mock RAGSystem with all dependencies mocked"""
    mock = Mock()
    mock.vector_store = mock_vector_store
    mock.ai_generator = mock_ai_generator
    mock.session_manager = mock_session_manager
    mock.tool_manager = mock_tool_manager
    mock.document_processor = mock_document_processor

    # Mock the query method
    mock.query = Mock(return_value=(
        "A RAG system is a Retrieval-Augmented Generation system.",
        [{"text": "Building RAG Applications - Lesson 1", "link": "https://example.com/lesson-1"}]
    ))

    # Mock course analytics
    mock.get_course_analytics = Mock(return_value={
        "total_courses": 1,
        "course_titles": ["Building RAG Applications"]
    })

    # Mock add_course_folder
    mock.add_course_folder = Mock(return_value=(1, 5))

    return mock


@pytest.fixture
def temp_test_file(tmp_path):
    """Create a temporary test file with sample course content"""
    file_path = tmp_path / "test_course.txt"
    content = """Course Title: Test Course
Course Link: https://example.com/course
Course Instructor: Test Instructor

Lesson 1: Introduction
Lesson Link: https://example.com/lesson-1
This is the introduction to the test course. It covers basic concepts.

Lesson 2: Advanced Topics
Lesson Link: https://example.com/lesson-2
This lesson covers more advanced topics in the subject matter.
"""
    file_path.write_text(content)
    return str(file_path)
