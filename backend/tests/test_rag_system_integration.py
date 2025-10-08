"""
Tests for RAGSystem integration in rag_system.py

Tests validate:
- query() end-to-end flow
- Source extraction from tools
- Session management integration
- Component orchestration
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import Mock, MagicMock, patch
from rag_system import RAGSystem
from config import Config


class TestRAGSystemInitialization:
    """Test RAG system initialization"""

    def test_initialization_with_config(self):
        """Test that RAGSystem initializes all components"""
        # Arrange
        config = Config()

        # Act
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'):
            rag = RAGSystem(config)

            # Assert
            assert rag.config == config
            assert hasattr(rag, 'vector_store')
            assert hasattr(rag, 'ai_generator')
            assert hasattr(rag, 'document_processor')
            assert hasattr(rag, 'session_manager')
            assert hasattr(rag, 'tool_manager')
            assert hasattr(rag, 'search_tool')
            assert hasattr(rag, 'outline_tool')


class TestRAGSystemQuery:
    """Test RAG system query processing"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = Config()

        # Create RAG system with mocked components
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'):
            self.rag = RAGSystem(self.config)

            # Mock the components
            self.rag.ai_generator = Mock()
            self.rag.session_manager = Mock()
            self.rag.tool_manager = Mock()

    def test_query_without_session(self):
        """Test query without session ID"""
        # Arrange
        self.rag.session_manager.get_conversation_history.return_value = None
        self.rag.ai_generator.generate_response.return_value = "This is Python"
        self.rag.tool_manager.get_last_sources.return_value = []

        # Act
        answer, sources = self.rag.query("What is Python?", session_id=None)

        # Assert
        assert answer == "This is Python"
        assert sources == []
        self.rag.ai_generator.generate_response.assert_called_once()
        # Session history should not be retrieved
        self.rag.session_manager.get_conversation_history.assert_not_called()

    def test_query_with_session(self):
        """Test query with session ID retrieves history"""
        # Arrange
        history = "User: Hello\nAssistant: Hi there"
        self.rag.session_manager.get_conversation_history.return_value = history
        self.rag.ai_generator.generate_response.return_value = "Python is great"
        self.rag.tool_manager.get_last_sources.return_value = []

        # Act
        answer, sources = self.rag.query("Tell me about Python", session_id="session_1")

        # Assert
        self.rag.session_manager.get_conversation_history.assert_called_once_with("session_1")
        call_kwargs = self.rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] == history

    def test_query_passes_tools_to_generator(self):
        """Test that query passes tool definitions to AI generator"""
        # Arrange
        mock_tool_defs = [
            {"name": "search_course_content", "description": "Search"},
            {"name": "get_course_outline", "description": "Outline"}
        ]
        self.rag.tool_manager.get_tool_definitions.return_value = mock_tool_defs
        self.rag.ai_generator.generate_response.return_value = "Answer"
        self.rag.tool_manager.get_last_sources.return_value = []

        # Act
        self.rag.query("Question")

        # Assert
        call_kwargs = self.rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["tools"] == mock_tool_defs
        assert call_kwargs["tool_manager"] == self.rag.tool_manager

    def test_query_extracts_sources(self):
        """Test that query extracts sources from tool manager"""
        # Arrange
        mock_sources = [
            {"text": "Python 101 - Lesson 1", "link": "https://example.com/lesson1"},
            {"text": "Python 101 - Lesson 2", "link": "https://example.com/lesson2"}
        ]
        self.rag.ai_generator.generate_response.return_value = "Answer"
        self.rag.tool_manager.get_last_sources.return_value = mock_sources

        # Act
        answer, sources = self.rag.query("Question")

        # Assert
        assert sources == mock_sources
        self.rag.tool_manager.get_last_sources.assert_called_once()

    def test_query_resets_sources_after_retrieval(self):
        """Test that sources are reset after each query"""
        # Arrange
        self.rag.ai_generator.generate_response.return_value = "Answer"
        self.rag.tool_manager.get_last_sources.return_value = [{"text": "Source", "link": None}]

        # Act
        self.rag.query("Question")

        # Assert
        self.rag.tool_manager.reset_sources.assert_called_once()

    def test_query_updates_conversation_history(self):
        """Test that query updates session history"""
        # Arrange
        query_text = "What is Python?"
        response_text = "Python is a programming language"
        self.rag.ai_generator.generate_response.return_value = response_text
        self.rag.tool_manager.get_last_sources.return_value = []

        # Act
        self.rag.query(query_text, session_id="session_1")

        # Assert
        self.rag.session_manager.add_exchange.assert_called_once_with(
            "session_1",
            query_text,
            response_text
        )

    def test_query_does_not_update_history_without_session(self):
        """Test that query doesn't update history if no session"""
        # Arrange
        self.rag.ai_generator.generate_response.return_value = "Answer"
        self.rag.tool_manager.get_last_sources.return_value = []

        # Act
        self.rag.query("Question", session_id=None)

        # Assert
        self.rag.session_manager.add_exchange.assert_not_called()

    def test_query_formats_prompt_correctly(self):
        """Test that query formats the prompt for AI generator"""
        # Arrange
        self.rag.ai_generator.generate_response.return_value = "Answer"
        self.rag.tool_manager.get_last_sources.return_value = []

        # Act
        self.rag.query("What is MCP?")

        # Assert
        call_args = self.rag.ai_generator.generate_response.call_args
        query_arg = call_args[1]["query"]
        assert "What is MCP?" in query_arg
        assert "Answer this question about course materials:" in query_arg


class TestRAGSystemSourceHandling:
    """Test source handling in RAG system"""

    def setup_method(self):
        """Set up test fixtures"""
        config = Config()
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'):
            self.rag = RAGSystem(config)
            self.rag.ai_generator = Mock()
            self.rag.tool_manager = Mock()

    def test_empty_sources_list(self):
        """Test handling of empty sources"""
        # Arrange
        self.rag.ai_generator.generate_response.return_value = "Answer"
        self.rag.tool_manager.get_last_sources.return_value = []

        # Act
        answer, sources = self.rag.query("Question")

        # Assert
        assert sources == []

    def test_sources_with_links(self):
        """Test sources with lesson links are preserved"""
        # Arrange
        expected_sources = [
            {"text": "Course A - Lesson 1", "link": "https://example.com/a1"},
            {"text": "Course B - Lesson 2", "link": "https://example.com/b2"}
        ]
        self.rag.ai_generator.generate_response.return_value = "Answer"
        self.rag.tool_manager.get_last_sources.return_value = expected_sources

        # Act
        answer, sources = self.rag.query("Question")

        # Assert
        assert sources == expected_sources
        assert sources[0]["link"] == "https://example.com/a1"
        assert sources[1]["link"] == "https://example.com/b2"

    def test_sources_without_links(self):
        """Test sources without links have None"""
        # Arrange
        expected_sources = [
            {"text": "Course A", "link": None}
        ]
        self.rag.ai_generator.generate_response.return_value = "Answer"
        self.rag.tool_manager.get_last_sources.return_value = expected_sources

        # Act
        answer, sources = self.rag.query("Question")

        # Assert
        assert sources[0]["link"] is None


class TestRAGSystemCourseAnalytics:
    """Test course analytics functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        config = Config()
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'):
            self.rag = RAGSystem(config)
            self.rag.vector_store = Mock()

    def test_get_course_analytics(self):
        """Test getting course analytics"""
        # Arrange
        self.rag.vector_store.get_course_count.return_value = 3
        self.rag.vector_store.get_existing_course_titles.return_value = [
            "Python 101",
            "Introduction to MCP",
            "Advanced Programming"
        ]

        # Act
        analytics = self.rag.get_course_analytics()

        # Assert
        assert analytics["total_courses"] == 3
        assert len(analytics["course_titles"]) == 3
        assert "Python 101" in analytics["course_titles"]
        self.rag.vector_store.get_course_count.assert_called_once()
        self.rag.vector_store.get_existing_course_titles.assert_called_once()


class TestRAGSystemToolRegistration:
    """Test tool registration"""

    def test_search_tool_registered(self):
        """Test that search tool is registered"""
        config = Config()
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'):
            rag = RAGSystem(config)

            # Check that tools were registered
            assert 'search_course_content' in rag.tool_manager.tools
            assert 'get_course_outline' in rag.tool_manager.tools

    def test_tool_definitions_available(self):
        """Test that tool definitions can be retrieved"""
        config = Config()
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'):
            rag = RAGSystem(config)

            # Get tool definitions
            tool_defs = rag.tool_manager.get_tool_definitions()

            # Should have 2 tools
            assert len(tool_defs) == 2
            tool_names = [tool["name"] for tool in tool_defs]
            assert "search_course_content" in tool_names
            assert "get_course_outline" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
