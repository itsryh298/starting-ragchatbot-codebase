# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application

**Quick Start (Git Bash on Windows):**
```bash
./run.sh
```

**Manual Start:**
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

**Access:**
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Dependency Management

**Install dependencies:**
```bash
uv sync
```

**Add a new dependency:**
```bash
uv add <package-name>
```

### Environment Setup

Required: `.env` file in root directory with:
```
ANTHROPIC_API_KEY=your-api-key-here
```

## Architecture Overview

### System Design

This is a **Retrieval-Augmented Generation (RAG)** system using Claude's tool-calling capabilities for intelligent course material queries.

**Core Pattern:**
User Query → FastAPI → RAG System → Claude (with tools) → Vector Search → Claude (with context) → Response

### Key Architectural Decisions

1. **Tool-Based Retrieval**: Claude decides when to search using the `search_course_content` tool rather than always retrieving context. This enables:
   - General knowledge questions answered directly
   - Course-specific questions trigger semantic search
   - Single search per query (enforced via system prompt)

2. **Two-Collection Vector Store**:
   - `course_catalog`: Course metadata (title, instructor, lessons) for semantic course name resolution
   - `course_content`: Chunked lesson content with course_title and lesson_number metadata

   This allows fuzzy course name matching (e.g., "MCP" → "Introduction to Model Context Protocol")

3. **Session-Based Conversation**: In-memory session manager maintains last N exchanges (configurable via `MAX_HISTORY` in config.py). Sessions are stateless across server restarts.

4. **Document Processing Pipeline**:
   ```
   Raw .txt → Extract metadata (title/instructor/link) → Split into lessons →
   Sentence-based chunking (800 chars, 100 overlap) → Add context prefixes →
   Store in ChromaDB with metadata
   ```

### Component Responsibilities

**`rag_system.py`** - Orchestrator
Coordinates all components. Entry point: `query(query, session_id)` returns `(answer, sources)`

**`ai_generator.py`** - Claude Integration
Handles tool-calling loop:
1. Send query with tools to Claude
2. If `stop_reason == "tool_use"`: execute tools, send results back
3. Return final response

**`vector_store.py`** - ChromaDB Interface
`search(query, course_name, lesson_number)`:
- Resolves course_name via semantic search on catalog
- Builds ChromaDB filter combining course + lesson
- Returns SearchResults with documents/metadata/distances

**`search_tools.py`** - Tool Definitions
Implements Tool interface for Claude tool-calling. `CourseSearchTool.execute()` formats results and tracks sources in `last_sources` for UI display.

**`document_processor.py`** - Parsing & Chunking
Expected document format:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 1: [title]
Lesson Link: [url]
[content]

Lesson 2: [title]
...
```

Chunks are prefixed with context: `"Course {title} Lesson {num} content: {chunk}"`

**`session_manager.py`** - Conversation Memory
Stores message pairs in-memory dict. `get_conversation_history()` returns formatted string for Claude's system prompt.

**`app.py`** - FastAPI Endpoints
- `POST /api/query`: Main query endpoint, creates session if needed
- `GET /api/courses`: Returns course analytics (count, titles)
- `startup_event`: Auto-loads documents from `../docs` on server start

### Configuration (config.py)

Key settings:
- `CHUNK_SIZE`: 800 characters (sentence-based boundaries)
- `CHUNK_OVERLAP`: 100 characters
- `MAX_RESULTS`: 5 search results returned to Claude
- `MAX_HISTORY`: 2 conversation exchanges (4 messages total)
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" (SentenceTransformers)

### Data Flow for Query Processing

1. **Frontend** sends `{query, session_id}` to `/api/query`
2. **FastAPI** calls `rag_system.query()`
3. **RAG System**:
   - Retrieves conversation history from session
   - Calls `ai_generator.generate_response()` with tools
4. **AI Generator**:
   - Sends to Claude with `search_course_content` tool definition
   - If Claude uses tool: executes via `tool_manager.execute_tool()`
   - Tool calls `vector_store.search()`
   - Sends search results back to Claude
   - Returns final answer
5. **RAG System**:
   - Extracts sources from `tool_manager.get_last_sources()`
   - Updates session history
   - Returns `(answer, sources)`
6. **FastAPI** returns JSON with answer, sources, session_id

### ChromaDB Schema

**course_catalog collection:**
```python
{
  "id": course_title,  # e.g., "Introduction to Model Context Protocol"
  "document": course_title,  # For embedding
  "metadata": {
    "title": str,
    "instructor": str,
    "course_link": str,
    "lessons_json": str,  # Serialized JSON of lessons array
    "lesson_count": int
  }
}
```

**course_content collection:**
```python
{
  "id": f"{course_title}_{chunk_index}",
  "document": chunk_content,  # With context prefix
  "metadata": {
    "course_title": str,
    "lesson_number": int,
    "chunk_index": int
  }
}
```

### System Prompt Strategy (ai_generator.py)

The static `SYSTEM_PROMPT` enforces:
- **One search per query maximum** - prevents tool overuse
- **No meta-commentary** - Claude doesn't explain its search process
- **Direct answers only** - no "Based on the search results..." preamble
- Brief, educational responses with examples when helpful

This prompt is critical for response quality and cost control.

### Adding New Course Documents

Place `.txt`, `.pdf`, or `.docx` files in `docs/` folder. On server restart, `startup_event` automatically:
1. Processes each document via `DocumentProcessor`
2. Checks against existing course titles (skips duplicates)
3. Adds course metadata to `course_catalog`
4. Adds chunked content to `course_content`

To force rebuild: `rag_system.add_course_folder(docs_path, clear_existing=True)`

### Frontend Architecture

Single-page vanilla JS application:
- **script.js**: Handles chat UI, fetch calls, markdown rendering (uses marked.js)
- **index.html**: Main UI with chat interface and course stats sidebar
- **style.css**: Styling with loading animations

FastAPI serves frontend as static files via `app.mount("/", StaticFiles(directory="../frontend"))` with custom no-cache headers for development.

## Common Debugging Notes

**ChromaDB path**: `./chroma_db` relative to `backend/` directory. Persists across restarts.

**Session IDs**: Generated sequentially as `session_1`, `session_2`, etc. Lost on server restart.

**Source tracking**: `CourseSearchTool` stores sources in `last_sources` list. Retrieved once per query then reset via `tool_manager.reset_sources()`.

**Tool execution flow**: Check `ai_generator._handle_tool_execution()` for the messages array construction - tool results must be formatted as `{"type": "tool_result", "tool_use_id": id, "content": str}`.

## Development Notes

- Always use uv to run server do not use pip directly
- Make sure to use uv to manage all dependencies
- Use uv to run python files