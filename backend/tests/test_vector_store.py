"""
Tests for VectorStore in vector_store.py

Tests validate:
- search() with different parameters
- MAX_RESULTS=0 bug demonstration
- Filter building logic
- Course name resolution
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import Mock, MagicMock, patch
from vector_store import VectorStore, SearchResults


class TestSearchResultsDataClass:
    """Test SearchResults data class"""

    def test_from_chroma_with_results(self):
        """Test creating SearchResults from ChromaDB response"""
        # Arrange
        chroma_response = {
            'documents': [['Doc 1', 'Doc 2']],
            'metadatas': [[{'course': 'A'}, {'course': 'B'}]],
            'distances': [[0.1, 0.2]]
        }

        # Act
        results = SearchResults.from_chroma(chroma_response)

        # Assert
        assert results.documents == ['Doc 1', 'Doc 2']
        assert results.metadata == [{'course': 'A'}, {'course': 'B'}]
        assert results.distances == [0.1, 0.2]
        assert results.error is None

    def test_from_chroma_empty(self):
        """Test creating SearchResults from empty ChromaDB response"""
        # Arrange
        chroma_response = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }

        # Act
        results = SearchResults.from_chroma(chroma_response)

        # Assert
        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.is_empty()

    def test_empty_with_error(self):
        """Test creating empty SearchResults with error message"""
        # Act
        results = SearchResults.empty("Database error")

        # Assert
        assert results.is_empty()
        assert results.error == "Database error"
        assert results.documents == []


class TestVectorStoreInitialization:
    """Test VectorStore initialization"""

    @patch('vector_store.chromadb.PersistentClient')
    def test_initialization(self, mock_client_class):
        """Test VectorStore initializes with correct parameters"""
        # Arrange
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        # Act
        store = VectorStore(
            chroma_path="./test_db",
            embedding_model="test-model",
            max_results=5
        )

        # Assert
        assert store.max_results == 5
        mock_client_class.assert_called_once()
        # Should create two collections
        assert mock_client.get_or_create_collection.call_count == 2

    @patch('vector_store.chromadb.PersistentClient')
    def test_max_results_zero_initialization(self, mock_client_class):
        """Test VectorStore with MAX_RESULTS=0 (the bug)"""
        # Arrange
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        # Act
        store = VectorStore(
            chroma_path="./test_db",
            embedding_model="test-model",
            max_results=0  # THE BUG!
        )

        # Assert
        assert store.max_results == 0  # This is the problem!


class TestVectorStoreSearch:
    """Test VectorStore search method"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('vector_store.chromadb.PersistentClient'):
            self.store = VectorStore("./test_db", "test-model", max_results=5)
            self.store.course_content = Mock()
            self.store.course_catalog = Mock()

    def test_search_without_filters(self):
        """Test search without course or lesson filters"""
        # Arrange
        mock_chroma_response = {
            'documents': [['Result 1', 'Result 2']],
            'metadatas': [[{'course_title': 'Course A'}, {'course_title': 'Course B'}]],
            'distances': [[0.1, 0.2]]
        }
        self.store.course_content.query.return_value = mock_chroma_response

        # Act
        results = self.store.search(query="test query")

        # Assert
        assert len(results.documents) == 2
        self.store.course_content.query.assert_called_once_with(
            query_texts=["test query"],
            n_results=5,
            where=None
        )

    def test_search_with_max_results_zero(self):
        """Test search with MAX_RESULTS=0 - demonstrates the bug"""
        # Arrange
        with patch('vector_store.chromadb.PersistentClient'):
            buggy_store = VectorStore("./test_db", "test-model", max_results=0)
            buggy_store.course_content = Mock()

            # ChromaDB returns empty when n_results=0
            buggy_store.course_content.query.return_value = {
                'documents': [[]],
                'metadatas': [[]],
                'distances': [[]]
            }

            # Act
            results = buggy_store.search(query="test query")

            # Assert
            assert results.is_empty()  # BUG: Returns no results!
            buggy_store.course_content.query.assert_called_once_with(
                query_texts=["test query"],
                n_results=0,  # THE PROBLEM: requesting 0 results
                where=None
            )

    def test_search_with_custom_limit(self):
        """Test search with custom limit parameter"""
        # Arrange
        mock_chroma_response = {
            'documents': [['Result 1', 'Result 2', 'Result 3']],
            'metadatas': [[{}, {}, {}]],
            'distances': [[0.1, 0.2, 0.3]]
        }
        self.store.course_content.query.return_value = mock_chroma_response

        # Act
        results = self.store.search(query="test", limit=3)

        # Assert
        self.store.course_content.query.assert_called_once_with(
            query_texts=["test"],
            n_results=3,  # Uses custom limit, not max_results
            where=None
        )

    def test_search_with_course_name_filter(self):
        """Test search with course name filter"""
        # Arrange
        # Mock course resolution
        self.store._resolve_course_name = Mock(return_value="Python 101")

        mock_chroma_response = {
            'documents': [['Python content']],
            'metadatas': [[{'course_title': 'Python 101'}]],
            'distances': [[0.1]]
        }
        self.store.course_content.query.return_value = mock_chroma_response

        # Act
        results = self.store.search(query="variables", course_name="Python")

        # Assert
        self.store._resolve_course_name.assert_called_once_with("Python")
        self.store.course_content.query.assert_called_once_with(
            query_texts=["variables"],
            n_results=5,
            where={"course_title": "Python 101"}
        )

    def test_search_with_course_not_found(self):
        """Test search when course name doesn't resolve"""
        # Arrange
        self.store._resolve_course_name = Mock(return_value=None)

        # Act
        results = self.store.search(query="test", course_name="Nonexistent Course")

        # Assert
        assert results.error is not None
        assert "No course found matching" in results.error
        assert "Nonexistent Course" in results.error

    def test_search_with_lesson_number_filter(self):
        """Test search with lesson number filter"""
        # Arrange
        mock_chroma_response = {
            'documents': [['Lesson 3 content']],
            'metadatas': [[{'lesson_number': 3}]],
            'distances': [[0.1]]
        }
        self.store.course_content.query.return_value = mock_chroma_response

        # Act
        results = self.store.search(query="test", lesson_number=3)

        # Assert
        self.store.course_content.query.assert_called_once_with(
            query_texts=["test"],
            n_results=5,
            where={"lesson_number": 3}
        )

    def test_search_with_both_filters(self):
        """Test search with both course and lesson filters"""
        # Arrange
        self.store._resolve_course_name = Mock(return_value="Python 101")

        mock_chroma_response = {
            'documents': [['Specific content']],
            'metadatas': [[{'course_title': 'Python 101', 'lesson_number': 2}]],
            'distances': [[0.1]]
        }
        self.store.course_content.query.return_value = mock_chroma_response

        # Act
        results = self.store.search(query="test", course_name="Python", lesson_number=2)

        # Assert
        self.store.course_content.query.assert_called_once_with(
            query_texts=["test"],
            n_results=5,
            where={"$and": [
                {"course_title": "Python 101"},
                {"lesson_number": 2}
            ]}
        )

    def test_search_exception_handling(self):
        """Test search handles exceptions gracefully"""
        # Arrange
        self.store.course_content.query.side_effect = Exception("Database error")

        # Act
        results = self.store.search(query="test")

        # Assert
        assert results.error is not None
        assert "Search error" in results.error
        assert "Database error" in results.error


class TestVectorStoreBuildFilter:
    """Test _build_filter method"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('vector_store.chromadb.PersistentClient'):
            self.store = VectorStore("./test_db", "test-model", max_results=5)

    def test_build_filter_no_parameters(self):
        """Test filter with no parameters"""
        result = self.store._build_filter(None, None)
        assert result is None

    def test_build_filter_course_only(self):
        """Test filter with only course title"""
        result = self.store._build_filter("Python 101", None)
        assert result == {"course_title": "Python 101"}

    def test_build_filter_lesson_only(self):
        """Test filter with only lesson number"""
        result = self.store._build_filter(None, 3)
        assert result == {"lesson_number": 3}

    def test_build_filter_both_parameters(self):
        """Test filter with both course and lesson"""
        result = self.store._build_filter("Python 101", 3)
        assert result == {"$and": [
            {"course_title": "Python 101"},
            {"lesson_number": 3}
        ]}


class TestVectorStoreResolveCourse:
    """Test _resolve_course_name method"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch('vector_store.chromadb.PersistentClient'):
            self.store = VectorStore("./test_db", "test-model", max_results=5)
            self.store.course_catalog = Mock()

    def test_resolve_course_name_success(self):
        """Test successful course name resolution"""
        # Arrange
        self.store.course_catalog.query.return_value = {
            'documents': [['Introduction to Model Context Protocol']],
            'metadatas': [[{'title': 'Introduction to Model Context Protocol'}]]
        }

        # Act
        result = self.store._resolve_course_name("MCP")

        # Assert
        assert result == "Introduction to Model Context Protocol"
        self.store.course_catalog.query.assert_called_once_with(
            query_texts=["MCP"],
            n_results=1
        )

    def test_resolve_course_name_not_found(self):
        """Test course name resolution when not found"""
        # Arrange
        self.store.course_catalog.query.return_value = {
            'documents': [[]],
            'metadatas': [[]]
        }

        # Act
        result = self.store._resolve_course_name("Nonexistent")

        # Assert
        assert result is None

    def test_resolve_course_name_exception(self):
        """Test course name resolution with exception"""
        # Arrange
        self.store.course_catalog.query.side_effect = Exception("DB error")

        # Act
        result = self.store._resolve_course_name("Test")

        # Assert
        assert result is None


class TestMaxResultsBugDemonstration:
    """Dedicated tests to demonstrate the MAX_RESULTS=0 bug"""

    def test_bug_with_zero_max_results(self):
        """CRITICAL TEST: Demonstrates MAX_RESULTS=0 causes no results"""
        with patch('vector_store.chromadb.PersistentClient'):
            # Simulate the bug from config.py
            buggy_store = VectorStore("./test_db", "test-model", max_results=0)
            buggy_store.course_content = Mock()

            # Even with available data, ChromaDB returns nothing with n_results=0
            buggy_store.course_content.query.return_value = {
                'documents': [[]],
                'metadatas': [[]],
                'distances': [[]]
            }

            # Act
            results = buggy_store.search(query="Python basics")

            # Assert
            assert results.is_empty(), "Bug confirmed: MAX_RESULTS=0 returns no results"
            # Verify it called with n_results=0
            call_kwargs = buggy_store.course_content.query.call_args[1]
            assert call_kwargs['n_results'] == 0, "ChromaDB called with 0 results"

    def test_fix_with_proper_max_results(self):
        """TEST FIX: Shows that MAX_RESULTS=5 works correctly"""
        with patch('vector_store.chromadb.PersistentClient'):
            # Simulate the fix
            fixed_store = VectorStore("./test_db", "test-model", max_results=5)
            fixed_store.course_content = Mock()

            # Now ChromaDB can return results
            fixed_store.course_content.query.return_value = {
                'documents': [['Python is a language', 'Variables store data']],
                'metadatas': [[{'course': 'Python'}, {'course': 'Python'}]],
                'distances': [[0.1, 0.2]]
            }

            # Act
            results = fixed_store.search(query="Python basics")

            # Assert
            assert not results.is_empty(), "Fix works: Returns results"
            assert len(results.documents) == 2, "Got expected number of results"
            # Verify it called with n_results=5
            call_kwargs = fixed_store.course_content.query.call_args[1]
            assert call_kwargs['n_results'] == 5, "ChromaDB called with 5 results"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
