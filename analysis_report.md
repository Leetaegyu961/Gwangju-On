# Project Analysis Report: Gwangju-On

## 1. Project Overview
**Gwangju-On** is an AI-powered travel course planner for Gwangju City. It leverages Google Gemini and LangGraph to generate personalized travel itineraries based on user preferences (survey data) and real-time data from Google Maps and Naver Blogs.

### Tech Stack
- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS, TMAP API.
- **Backend**: FastAPI, Python 3.13+, Poetry.
- **Main Agent**: LangGraph (Complex Workflow, Parallel Generation).
- **Mini Agent**: Custom Node-based Architecture (Lightweight, Async).
- **LLM**: Google Gemini (via `langchain-google-genai`).
- **Data Sources**: Google Places API (Location/Rating), Naver Search API (Blog Reviews), Public Data (Gwangju Food List).

## 2. Architecture Mapping

### System Data Flow
```mermaid
graph LR
    User[Frontend (Next.js)] -->|REST API (JSON)| Backend[FastAPI]
    Backend -->|Invoke| MainAgent[LangGraph Agent]
    
    subgraph "Main Agent Pipeline"
        QP[Query Planner] -->|Search Queries| Google[Google Maps API]
        Google -->|Place Data| Naver[Naver Blog Search]
        Naver -->|Enriched Data| Scoring[Scoring Node v4]
        Scoring -->|Top Places| ParallelGen[Parallel Course Generation]
        ParallelGen -->|JSON| Agg[Aggregator]
    end
    
    Agg -->|Final Answer| Backend
    Backend -->|ChatResponse| User
```

### Key Components

#### A. Backend (`backend/`)
- **`api/chat.py`**: The core entry point. It retrieves user survey data, invokes the Agent, and processes the JSON output into `EvidenceCard` objects for the frontend.
- **`api/photo.py`**: Proxies Google Place photos to avoid CORS issues on the frontend.
- **`models/chat.py`**: Defines the data contracts (`ChatRequest`, `ChatResponse`, `EvidenceCard`).

#### B. Main Agent (`src/agent/`)
- **`graph.py`**: Defines the execution workflow. Currently implements a **Static Pipeline** with parallel generation:
  1. `query_planner`: Analyzes intent and generates 3 themes + search queries.
  2. `google_place_search`: Fetches raw place data.
  3. `naver_blog_search`: Enriches place data with blog reviews.
  4. `scoring`: "Scoring Node v4" uses LLM for sentiment analysis (Taste/Service/Value/Revisit) + Public Data scoring.
  5. `generate_course_{1,2,3}`: Parallel LLM calls to generate 3 distinct courses.
  6. `aggregator`: Combines results.
- **Note**: The **Agentic RAG** strategy (iterative retrieval) is planned but not yet implemented.

#### C. Mini Agent (`src/mini_agent/`)
- **Purpose**: A lightweight, standalone agent for quick place lookup and summarization.
- **Architecture**: Orchestrator (`MiniAgent`) managing independent nodes (`PlaceSearchNode`, `LLMNode`).
- **Features**: Fully asynchronous I/O, independent LangSmith tracing per node.

#### D. Frontend (`frontend/`)
- **`services/geminiService.ts`**: Handles API communication.
- **`screens/ChatScreen.tsx`**: Manages chat state. When `isDecisionPoint` is true, it saves the course to `localStorage` and redirects to `/map`.
- **`screens/MapView.tsx`**: Visualizes the generated course using TMAP.

## 3. Current Status & Gaps
- **Implemented**: 
  - Full Frontend-Backend-Agent connection.
  - "Scoring Node v4" with batch LLM processing.
  - Parallel Course Generation (3 themes).
  - Mini Agent (Independent module).
  - TMAP visualization.
- **Pending / Planned**:
  - **Agentic RAG**: The strategy document proposes adding `rag_retrieval` and `context_evaluator` nodes.
  - **Vector Store**: `extracted_keywords.json` exists, but the vector search node is not active in the main graph.

## 4. Readiness Confirmation
The codebase is indexed and the architecture is mapped. The system supports both a complex LangGraph pipeline (Main Agent) and a lightweight node-based pipeline (Mini Agent).

**Ready to proceed.**
