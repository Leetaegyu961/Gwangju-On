# End-to-End Integration Plan: AI Travel Agent & TMAP Course Generation

## Overview
This document outlines the complete integration plan to connect the AI Agent (Backend), User Survey (Frontend), and TMAP API (Frontend Map Rendering).

## 1. Data Flow Architecture

### Phase 1: User Onboarding & Survey
1.  **User Input**: User selects Gender, Age, Themes, Companions, and Budget in `ProfileSetupScreen` & `SurveyScreen`.
2.  **Data Sync**:
    -   Frontend calls `POST /api/user/onboard` (creates session, returns `userId`).
    -   Frontend calls `POST /api/user/survey` (updates preferences for `userId`).
    -   **Storage**: Backend stores this in an in-memory `USER_DB` (or Redis/DB in production).

### Phase 2: AI Agent Processing
1.  **User Request**: User enters a location (e.g., "Dongmyeong-dong") in `ChatScreen`.
2.  **Agent Invocation**:
    -   Frontend sends `POST /api/chat` with `{ message: "...", userId: "..." }`.
    -   Backend retrieves `survey_data` using `userId`.
    -   **Graph Execution**: `AgentState` is initialized with `survey_data`.
3.  **Intelligence Layer**:
    -   **QueryPlanner**: Generates search queries optimized for the user's demographic (e.g., "Romantic dinner spots in Dongmyeong-dong").
    -   **SearchNode**: Fetches Google Places & Naver Blog reviews.
    -   **LLMNode**: Synthesizes a response and outputs strictly formatted **JSON**.
        ```json
        {
          "answer": "Here are 3 romantic spots...",
          "courses": [
            { "name": "...", "lat": 35.1, "lng": 126.9, "type": "restaurant" }
          ]
        }
        ```

### Phase 3: Response & Visualization
1.  **Response Parsing**: Backend parses the JSON, converts `courses` into `EvidenceCard` objects, and returns them to Frontend.
2.  **UI Rendering**:
    -   `ChatScreen` displays the text answer.
    -   If `courses` exist, it shows a "Create Course" card (`isDecisionPoint=true`).
3.  **Map Handoff**:
    -   When user clicks "Create Course", Frontend saves the course data to `localStorage`.
    -   Navigate to `MapView`.
    -   `MapView` reads `localStorage`, initializes **TMAP**, and draws markers/lines for the course.

---

## 2. Detailed Implementation Steps

### Step 1: Backend Parsing Logic (Refinement)
-   **Current Status**: Implemented basic JSON parsing in `api/chat.py`.
-   **Action**: Ensure `courses` list from JSON is correctly mapped to `EvidenceCard.placeId` or a new field `course_data` in the API response to avoid data loss (coordinates).

### Step 2: Frontend Data Handoff
-   **Current Status**: `ChatScreen` receives `evidenceCards` but doesn't persist them for the map.
-   **Action**:
    -   Modify `ChatScreen`'s "Create Course" button handler.
    -   Extract coordinates (`lat`, `lng`) from the AI response (needs to be passed through `EvidenceCard` or a separate `data` field).
    -   Save to `localStorage.setItem('current_course', ...)` before routing to `/map`.

### Step 3: TMAP Integration
-   **Current Status**: `MapView.tsx` exists but uses mock data.
-   **Action**:
    -   Update `MapView` to `useEffect` load data from `localStorage.getItem('current_course')`.
    -   Use `new Tmapv2.Marker` to iterate through the loaded points and display them.
    -   Use `Tmapv2.Polyline` (optional) to connect the points.

### Step 4: Testing & Validation
-   [ ] **Survey Sync**: Check backend logs for `[Survey Update]`.
-   [ ] **Agent Execution**: Check backend logs for `[Agent Done] Output Length`.
-   [ ] **JSON Format**: Verify LLM outputs valid JSON with `lat`/`lng`.
-   [ ] **Map Rendering**: Verify TMAP draws markers at the coordinates provided by the AI.

## 3. Future Improvements
-   **DB Persistence**: Move `USER_DB` to MongoDB/PostgreSQL.
-   **RAG**: Index Naver Blog data into a Vector DB for faster retrieval.
-   **Real-time Stream**: Use WebSocket or Server-Sent Events (SSE) for faster chat responses.
