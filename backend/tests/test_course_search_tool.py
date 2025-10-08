"""
Tests for CourseSearchTool in search_tools.py

Tests validate:
- execute() method with various search scenarios
- Result formatting with course and lesson context
- Source tracking with lesson links
- Error handling
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import Mock, MagicMock
from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test CourseSearchTool.execute() method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_vector_store = Mock()
        self.tool = CourseSearchTool(self.mock_vector_store)

    def test_execute_with_valid_results(self):
        """Test execute returns formatted results when search succeeds"""
        # Arrange
        mock_results = SearchResults(
            documents=["Content about Python basics", "Content about variables"],
            metadata=[
                {"course_title": "Python 101", "lesson_number": 1},
                {"course_title": "Python 101", "lesson_number": 2}
            ],
            distances=[0.1, 0.2],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        # Act
        result = self.tool.execute(query="What is Python?")

        # Assert
        assert "[Python 101 - Lesson 1]" in result
        assert "Content about Python basics" in result
        assert "[Python 101 - Lesson 2]" in result
        assert "Content about variables" in result
        self.mock_vector_store.search.assert_called_once_with(
            query="What is Python?",
            course_name=None,
            lesson_number=None
        )

    def test_execute_with_course_filter(self):
        """Test execute passes course_name filter to search"""
        # Arrange
        mock_results = SearchResults(
            documents=["MCP content"],
            metadata=[{"course_title": "Introduction to Model Context Protocol", "lesson_number": 1}],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.return_value = None

        # Act
        result = self.tool.execute(query="What is MCP?", course_name="MCP")

        # Assert
        assert "Introduction to Model Context Protocol" in result
        self.mock_vector_store.search.assert_called_once_with(
            query="What is MCP?",
            course_name="MCP",
            lesson_number=None
        )

    def test_execute_with_lesson_filter(self):
        """Test execute passes lesson_number filter to search"""
        # Arrange
        mock_results = SearchResults(
            documents=["Lesson 3 content"],
            metadata=[{"course_title": "Python 101", "lesson_number": 3}],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.return_value = None

        # Act
        result = self.tool.execute(query="lesson content", lesson_number=3)

        # Assert
        assert "Lesson 3" in result
        self.mock_vector_store.search.assert_called_once_with(
            query="lesson content",
            course_name=None,
            lesson_number=3
        )

    def test_execute_with_both_filters(self):
        """Test execute with both course_name and lesson_number"""
        # Arrange
        mock_results = SearchResults(
            documents=["Specific content"],
            metadata=[{"course_title": "Python 101", "lesson_number": 2}],
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson2"

        # Act
        result = self.tool.execute(query="content", course_name="Python", lesson_number=2)

        # Assert
        self.mock_vector_store.search.assert_called_once_with(
            query="content",
            course_name="Python",
            lesson_number=2
        )

    def test_execute_with_empty_results(self):
        """Test execute returns appropriate message when no results found"""
        # Arrange
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        # Act
        result = self.tool.execute(query="nonexistent topic")

        # Assert
        assert "No relevant content found" in result

    def test_execute_with_empty_results_and_course_filter(self):
        """Test execute includes filter info in empty results message"""
        # Arrange
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        # Act
        result = self.tool.execute(query="topic", course_name="Python 101")

        # Assert
        assert "No relevant content found" in result
        assert "Python 101" in result

    def test_execute_with_empty_results_and_lesson_filter(self):
        """Test execute includes lesson number in empty results message"""
        # Arrange
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        # Act
        result = self.tool.execute(query="topic", lesson_number=5)

        # Assert
        assert "No relevant content found" in result
        assert "lesson 5" in result

    def test_execute_with_search_error(self):
        """Test execute returns error message when search fails"""
        # Arrange
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Database connection failed"
        )
        self.mock_vector_store.search.return_value = mock_results

        # Act
        result = self.tool.execute(query="any query")

        # Assert
        assert "Database connection failed" in result

    def test_source_tracking_with_links(self):
        """Test that last_sources includes lesson links"""
        # Arrange
        mock_results = SearchResults(
            documents=["Content 1", "Content 2"],
            metadata=[
                {"course_title": "Python 101", "lesson_number": 1},
                {"course_title": "Python 101", "lesson_number": 2}
            ],
            distances=[0.1, 0.2],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.side_effect = [
            "https://example.com/lesson1",
            "https://example.com/lesson2"
        ]

        # Act
        self.tool.execute(query="Python")

        # Assert
        assert len(self.tool.last_sources) == 2
        assert self.tool.last_sources[0]["text"] == "Python 101 - Lesson 1"
        assert self.tool.last_sources[0]["link"] == "https://example.com/lesson1"
        assert self.tool.last_sources[1]["text"] == "Python 101 - Lesson 2"
        assert self.tool.last_sources[1]["link"] == "https://example.com/lesson2"

    def test_source_tracking_without_lesson_number(self):
        """Test source tracking when lesson_number is missing"""
        # Arrange
        mock_results = SearchResults(
            documents=["Content without lesson"],
            metadata=[{"course_title": "Python 101"}],  # No lesson_number
            distances=[0.1],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        # Act
        self.tool.execute(query="Python")

        # Assert
        assert len(self.tool.last_sources) == 1
        assert self.tool.last_sources[0]["text"] == "Python 101"
        assert self.tool.last_sources[0]["link"] is None

    def test_format_results_multiple_documents(self):
        """Test that multiple documents are properly separated"""
        # Arrange
        mock_results = SearchResults(
            documents=["Doc 1", "Doc 2", "Doc 3"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
                {"course_title": "Course A", "lesson_number": 3}
            ],
            distances=[0.1, 0.2, 0.3],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.return_value = None

        # Act
        result = self.tool.execute(query="test")

        # Assert
        # Documents should be separated by double newlines
        assert result.count("\n\n") >= 2  # At least 2 separators for 3 docs

    def test_get_tool_definition(self):
        """Test that tool definition is properly formatted"""
        # Act
        definition = self.tool.get_tool_definition()

        # Assert
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert "query" in definition["input_schema"]["properties"]
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["query"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
