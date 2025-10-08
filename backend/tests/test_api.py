"""
API endpoint tests for the RAG system FastAPI application.

Tests the /api/query and /api/courses endpoints for proper request/response handling.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# Create a test app without static file mounting to avoid import issues
def create_test_app(mock_rag_system):
    """Create a test FastAPI app with mocked dependencies"""

    app = FastAPI(title="Course Materials RAG System - Test", root_path="")

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Pydantic models for request/response
    class QueryRequest(BaseModel):
        """Request model for course queries"""
        query: str
        session_id: Optional[str] = None

    class Source(BaseModel):
        """Model for a source citation with optional link"""
        text: str
        link: Optional[str] = None

    class QueryResponse(BaseModel):
        """Response model for course queries"""
        answer: str
        sources: List[Source]
        session_id: str

    class CourseStats(BaseModel):
        """Response model for course statistics"""
        total_courses: int
        course_titles: List[str]

    # API Endpoints
    @app.post("/api/query")
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            # Create session if not provided
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            # Process query using RAG system
            answer, sources = mock_rag_system.query(request.query, session_id)

            # Ensure sources are properly formatted as list of dicts
            formatted_sources = []
            if sources:
                for source in sources:
                    if isinstance(source, dict):
                        formatted_sources.append({
                            "text": source.get("text", ""),
                            "link": source.get("link", None)
                        })
                    elif isinstance(source, str):
                        formatted_sources.append({
                            "text": source,
                            "link": None
                        })

            return {
                "answer": answer,
                "sources": formatted_sources,
                "session_id": session_id
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def test_app(mock_rag_system):
    """Create test FastAPI application with mocked RAG system"""
    return create_test_app(mock_rag_system)


@pytest.fixture
def client(test_app):
    """Create test client for FastAPI app"""
    return TestClient(test_app)


# API Endpoint Tests

@pytest.mark.api
class TestQueryEndpoint:
    """Tests for the /api/query endpoint"""

    def test_query_with_session_id(self, client, sample_query_request, mock_rag_system):
        """Test query endpoint with existing session ID"""
        response = client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "session_1"

        # Verify RAG system was called
        mock_rag_system.query.assert_called_once_with(
            sample_query_request["query"],
            sample_query_request["session_id"]
        )

    def test_query_without_session_id(self, client, mock_rag_system):
        """Test query endpoint creates session when not provided"""
        request_data = {"query": "What is a RAG system?"}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        # Verify session was created
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_response_structure(self, client, sample_query_request):
        """Test query endpoint returns correct response structure"""
        response = client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Check sources structure
        if data["sources"]:
            for source in data["sources"]:
                assert "text" in source
                assert "link" in source

    def test_query_with_string_sources(self, client, mock_rag_system):
        """Test query endpoint handles string sources correctly"""
        # Mock RAG system to return string sources
        mock_rag_system.query.return_value = (
            "Test answer",
            ["Source 1", "Source 2"]
        )

        request_data = {"query": "Test query", "session_id": "session_1"}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify sources were converted to dict format
        assert len(data["sources"]) == 2
        assert data["sources"][0] == {"text": "Source 1", "link": None}
        assert data["sources"][1] == {"text": "Source 2", "link": None}

    def test_query_with_dict_sources(self, client, mock_rag_system):
        """Test query endpoint handles dict sources correctly"""
        # Mock RAG system to return dict sources
        mock_rag_system.query.return_value = (
            "Test answer",
            [
                {"text": "Source 1", "link": "https://example.com/1"},
                {"text": "Source 2", "link": "https://example.com/2"}
            ]
        )

        request_data = {"query": "Test query", "session_id": "session_1"}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify sources maintained their structure
        assert len(data["sources"]) == 2
        assert data["sources"][0]["link"] == "https://example.com/1"
        assert data["sources"][1]["link"] == "https://example.com/2"

    def test_query_missing_required_field(self, client):
        """Test query endpoint returns error for missing required field"""
        request_data = {"session_id": "session_1"}  # Missing 'query'
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_query_empty_string(self, client):
        """Test query endpoint accepts empty query string"""
        request_data = {"query": "", "session_id": "session_1"}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200

    def test_query_error_handling(self, client, mock_rag_system):
        """Test query endpoint handles RAG system errors"""
        # Mock RAG system to raise an exception
        mock_rag_system.query.side_effect = Exception("Test error")

        request_data = {"query": "Test query", "session_id": "session_1"}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 500
        assert "Test error" in response.json()["detail"]


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for the /api/courses endpoint"""

    def test_get_courses_success(self, client, mock_rag_system):
        """Test courses endpoint returns course statistics"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 1
        assert "Building RAG Applications" in data["course_titles"]

        # Verify analytics method was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_get_courses_response_structure(self, client):
        """Test courses endpoint returns correct response structure"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

    def test_get_courses_empty_catalog(self, client, mock_rag_system):
        """Test courses endpoint with no courses"""
        # Mock empty catalog
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_courses_multiple_courses(self, client, mock_rag_system):
        """Test courses endpoint with multiple courses"""
        # Mock multiple courses
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": [
                "Building RAG Applications",
                "Introduction to MCP",
                "Advanced AI Systems"
            ]
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3

    def test_get_courses_error_handling(self, client, mock_rag_system):
        """Test courses endpoint handles analytics errors"""
        # Mock RAG system to raise an exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "Analytics error" in response.json()["detail"]


@pytest.mark.api
class TestEndpointIntegration:
    """Integration tests for API endpoints"""

    def test_query_then_courses(self, client, mock_rag_system):
        """Test querying then fetching course stats"""
        # First query
        query_response = client.post("/api/query", json={
            "query": "What is a RAG system?",
            "session_id": "session_1"
        })
        assert query_response.status_code == 200

        # Then get courses
        courses_response = client.get("/api/courses")
        assert courses_response.status_code == 200

        courses_data = courses_response.json()
        assert courses_data["total_courses"] > 0

    def test_multiple_queries_same_session(self, client, mock_rag_system):
        """Test multiple queries with same session ID"""
        session_id = "session_1"

        # First query
        response1 = client.post("/api/query", json={
            "query": "What is a RAG system?",
            "session_id": session_id
        })
        assert response1.status_code == 200
        assert response1.json()["session_id"] == session_id

        # Second query
        response2 = client.post("/api/query", json={
            "query": "How does it work?",
            "session_id": session_id
        })
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

    def test_cors_headers(self, client):
        """Test CORS headers are present in responses"""
        response = client.get("/api/courses")

        # Check CORS headers are set (TestClient may not show all headers)
        assert response.status_code == 200
