# RAG System Query Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Browser)                              │
│                                script.js                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ User enters query
                                      │ sendMessage() called
                                      ▼
                        ┌─────────────────────────────┐
                        │  POST /api/query            │
                        │  {                          │
                        │    query: "user question",  │
                        │    session_id: "session_1"  │
                        │  }                          │
                        └─────────────────────────────┘
                                      │
                                      │ HTTP Request
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FASTAPI BACKEND                                   │
│                                app.py                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  @app.post("/api/query")                                                    │
│  async def query_documents(request):                                        │
│      session_id = request.session_id or create_session()                   │
│      answer, sources = rag_system.query(request.query, session_id)         │
│      return QueryResponse(answer, sources, session_id)                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Calls rag_system.query()
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            RAG SYSTEM ORCHESTRATOR                           │
│                              rag_system.py                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  query(query, session_id):                                                  │
│    1. Build prompt                                                          │
│    2. Get conversation history ────────────┐                                │
│    3. Generate AI response                 │                                │
│    4. Get sources from tool manager        │                                │
│    5. Update conversation history ─────────┤                                │
│    6. Return (answer, sources)             │                                │
│                                            │                                │
└────────────────────────────────────────────┼────────────────────────────────┘
                    │                        │
                    │                        ▼
                    │          ┌──────────────────────────────┐
                    │          │   SESSION MANAGER            │
                    │          │   session_manager.py         │
                    │          ├──────────────────────────────┤
                    │          │  • get_conversation_history()│
                    │          │  • add_exchange(user, ai)    │
                    │          │  • Keep last 5 exchanges     │
                    │          └──────────────────────────────┘
                    │
                    │ Calls ai_generator.generate_response()
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI GENERATOR                                    │
│                            ai_generator.py                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  generate_response(query, history, tools, tool_manager):                    │
│    1. Build system prompt + conversation history                            │
│    2. Call Claude API with tools                                            │
│    3. If stop_reason == "tool_use":                                         │
│         ├─> Execute tools                                                   │
│         ├─> Send results back to Claude                                     │
│         └─> Get final response                                              │
│    4. Return response text                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
         │                                    │
         │ Anthropic API Call                 │ Tool Execution Needed
         ▼                                    ▼
┌──────────────────────────┐    ┌────────────────────────────────────────────┐
│   ANTHROPIC CLAUDE API   │    │         TOOL MANAGER & SEARCH TOOL         │
│                          │    │           search_tools.py                  │
│  • Model: claude-3       │    ├────────────────────────────────────────────┤
│  • Temperature: 0        │    │                                            │
│  • Max tokens: 800       │    │  execute_tool("search_course_content"):    │
│  • Tools: Available      │    │    1. Extract parameters (query, course,   │
│  • Returns: text or      │    │       lesson_number)                       │
│    tool_use request      │    │    2. Call CourseSearchTool.execute()      │
│                          │    │    3. Format results                       │
└──────────────────────────┘    │    4. Track sources (last_sources)         │
                                └────────────────────────────────────────────┘
                                                 │
                                                 │ Calls vector_store.search()
                                                 ▼
                                ┌────────────────────────────────────────────┐
                                │          VECTOR STORE                      │
                                │         vector_store.py                    │
                                ├────────────────────────────────────────────┤
                                │                                            │
                                │  search(query, course_name, lesson_number):│
                                │    1. Resolve course name (semantic match) │
                                │       └─> Query course_catalog collection  │
                                │    2. Build filter (course + lesson)       │
                                │    3. Query course_content collection      │
                                │    4. Return SearchResults                 │
                                │                                            │
                                └────────────────────────────────────────────┘
                                                 │
                                                 │ ChromaDB Vector Query
                                                 ▼
                                ┌────────────────────────────────────────────┐
                                │            ChromaDB                        │
                                │         (Vector Database)                  │
                                ├────────────────────────────────────────────┤
                                │                                            │
                                │  Collections:                              │
                                │  • course_catalog (metadata)               │
                                │  • course_content (chunks)                 │
                                │                                            │
                                │  Embedding Model:                          │
                                │  • Sentence Transformers                   │
                                │  • all-MiniLM-L6-v2                        │
                                │                                            │
                                │  Returns:                                  │
                                │  • Top K similar documents                 │
                                │  • Metadata (course, lesson)               │
                                │  • Distance scores                         │
                                │                                            │
                                └────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                              RESPONSE FLOW (Back Up)
═══════════════════════════════════════════════════════════════════════════════

ChromaDB Results
    │
    ├─> [Document 1: "content...", metadata: {course, lesson}]
    ├─> [Document 2: "content...", metadata: {course, lesson}]
    └─> [Document 3: "content...", metadata: {course, lesson}]
    │
    ▼
Vector Store → Formats SearchResults
    │
    ▼
Search Tool → Formats with headers & tracks sources
    │
    │   Example:
    │   "[Course 1 - Lesson 2]
    │   This content explains..."
    │
    ▼
Tool Manager → Returns to AI Generator
    │
    ▼
Claude API → Receives tool results, generates final answer
    │
    │   "Based on the course materials, the answer is..."
    │
    ▼
AI Generator → Returns response text
    │
    ▼
RAG System → Extracts sources from tool_manager.get_last_sources()
    │
    │   sources = ["Course 1 - Lesson 2", "Course 1 - Lesson 3"]
    │
    ▼
RAG System → Updates session history
    │
    ▼
FastAPI → Returns JSON Response
    │
    │   {
    │     "answer": "Based on the course materials...",
    │     "sources": ["Course 1 - Lesson 2", ...],
    │     "session_id": "session_1"
    │   }
    │
    ▼
Frontend → Renders markdown answer + collapsible sources
    │
    └─> User sees formatted response with sources


═══════════════════════════════════════════════════════════════════════════════
                                  DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

User Query
    ↓
Session Context (Previous Q&A pairs)
    ↓
AI Prompt (Query + History + System Instructions)
    ↓
Claude Decision (Use tool or answer directly)
    ↓
[IF TOOL USE] Vector Search (Semantic similarity)
    ↓
Relevant Course Chunks
    ↓
Claude + Context → Final Answer
    ↓
Response + Sources + Session Updated
    ↓
UI Display


═══════════════════════════════════════════════════════════════════════════════
                              KEY TECHNOLOGIES
═══════════════════════════════════════════════════════════════════════════════

┌────────────────┬─────────────────────┬──────────────────────────────┐
│ Layer          │ Technology          │ Purpose                      │
├────────────────┼─────────────────────┼──────────────────────────────┤
│ Frontend       │ Vanilla JS          │ User interaction             │
│ API            │ FastAPI             │ REST endpoints               │
│ Orchestration  │ RAGSystem (Python)  │ Coordinate components        │
│ AI             │ Anthropic Claude    │ Generate responses           │
│ Tools          │ Claude Tool Use     │ Function calling             │
│ Vector DB      │ ChromaDB            │ Semantic search              │
│ Embeddings     │ Sentence Transform. │ Text → Vector conversion     │
│ Session        │ In-memory Dict      │ Conversation history         │
└────────────────┴─────────────────────┴──────────────────────────────┘
```
