# Agentic Research Workspace

This project has been upgraded from a single-document PDF QA demo into a production-oriented backend foundation for an Agentic Research Workspace. The frontend is intentionally minimal, but the backend structure, API surface, storage model, and deployment assets are aligned to the SaaS platform described in your requirements.

## What changed

- Replaced the single global FAISS flow with a service-oriented FastAPI backend.
- Added JWT auth, user roles, workspaces, documents, chunks, research sessions, reports, citations, and agent runs.
- Switched the architecture target to PostgreSQL, Qdrant, and MinIO.
- Added a hybrid retrieval service contract, agent orchestration service, comparison service, research service, and MCP connector registry.
- Added `docker-compose.yml`, Kubernetes deployment stubs, and a minimal React operations console.

## Folder structure

```text
backend/
  app/
    api/
      routes/
    agents/
    core/
    db/
    models/
    retrieval/
    schemas/
    services/
    workers/
  backend.py
  requirements.txt
  Dockerfile
  sample.env
frontend/
  src/
    App.jsx
    App.css
    services/api.js
k8s/
docker-compose.yml
```

## System architecture

### Runtime layers

1. React frontend for workspace operations, search, and research runs.
2. FastAPI gateway for auth, workspace APIs, ingestion, retrieval, reports, comparisons, and MCP discovery.
3. Background workers for ingestion, embeddings, sparse indexing, exports, and connector sync.
4. PostgreSQL for system-of-record entities.
5. Qdrant for dense vectors with metadata filtering and workspace isolation.
6. MinIO for raw uploads, generated reports, and exports.
7. LangGraph for planner, tool routing, reflection, and durable agent runs.
8. LangSmith for traces, prompt evaluation, tool telemetry, and token usage.

### Core data flow

1. User authenticates and creates a workspace.
2. User uploads documents into a workspace.
3. API stores document metadata in PostgreSQL and file objects in MinIO.
4. Worker extracts content, chunks it, writes chunk metadata to PostgreSQL, embeds chunks, and indexes them in Qdrant.
5. Sparse index is refreshed for BM25 retrieval.
6. Search or research requests go through the agent planner.
7. Agent runs hybrid retrieval: dense plus sparse, then reranking.
8. Agent may call web search and MCP tools.
9. Final answer is returned only with citations.
10. Research reports are persisted and can be resumed later.

## Database schema

### Implemented tables

- `users`
- `workspaces`
- `documents`
- `chunks`
- `research_sessions`
- `reports`
- `citations`
- `agent_runs`

### Important fields

- `documents`: `workspace_id`, `filename`, `mime_type`, `storage_path`, `status`
- `chunks`: `document_id`, `workspace_id`, `chunk_id`, `page_number`, `content`, `source_type`, `vector_id`
- `agent_runs`: `run_type`, `query`, `response`, `status`, `plan`, `trace_id`
- `citations`: `document_name`, `page_number`, `reference_text`

### Production extensions to add next

- `connector_accounts`
- `workspace_members`
- `report_exports`
- `tool_invocations`
- `retrieval_evaluations`
- `api_keys`
- `audit_logs`

## API specification

### Authentication

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

### Workspaces

- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces`

### Documents

- `GET /api/v1/documents/{workspace_id}`
- `POST /api/v1/documents/{workspace_id}/upload`

### Search and agents

- `POST /api/v1/search`
- `POST /api/v1/research/runs`

### Reports

- `GET /api/v1/reports/{workspace_id}`
- `POST /api/v1/reports`

### Comparison

- `POST /api/v1/comparisons`

### MCP

- `GET /api/v1/mcp/connectors`

## Retrieval pipeline

### Target production design

1. Dense retrieval in Qdrant using chunk embeddings.
2. Sparse retrieval using BM25 over workspace chunk text.
3. Candidate merge and deduplication by `chunk_id`.
4. Cross-encoder reranking.
5. Context packing with citation metadata.
6. Response generation with citation validation.

### Current repo implementation

- The repository now exposes the retrieval service boundary and citation-first answer contract.
- For local development without external services, the current code uses an in-process retrieval index as a transitional implementation.
- Qdrant integration is the intended next execution-layer swap without changing API contracts.

## LangGraph design

### Planned graph

1. `planner`
2. `workspace_search_tool`
3. `web_search_tool`
4. `comparison_tool`
5. `research_synthesizer`
6. `citation_validator`
7. `final_answer`

### State carried through the graph

- user query
- active workspace
- retrieved evidence
- web findings
- MCP tool outputs
- reasoning plan
- reflection notes
- citations
- final answer

### Durability

- Persist graph checkpoints in PostgreSQL.
- Resume long-running research sessions from saved state.
- Emit traces to LangSmith per node transition.

## Tool architecture

### First-class tools

- Document Search Tool
- Workspace Search Tool
- Web Search Tool
- Document Comparison Tool
- Research Tool
- Report Generator Tool
- Citation Tool
- MCP Connector Tool

### Design principles

- Each tool is isolated behind a service boundary.
- Tool inputs and outputs are typed with Pydantic schemas.
- Tools can be selected by an agent planner or invoked directly by REST endpoints.

## MCP integration design

### Supported connector targets

- GitHub MCP
- Google Drive MCP
- Notion MCP
- Slack MCP
- Confluence MCP

### Connector contract

- OAuth-based account linking
- connector-specific sync jobs
- normalized ingestion events
- tool capabilities advertised to the planner
- per-workspace access controls

## Report generation

### Formats

- Markdown
- PDF
- DOCX

### Report sections

- Executive Summary
- Key Findings
- Technical Analysis
- Recommendations
- References

### Current repo implementation

- Markdown persistence is implemented.
- PDF and DOCX export should be added as worker tasks using WeasyPrint and `python-docx`.

## Deployment architecture

### Docker

- `api`
- `worker`
- `postgres`
- `qdrant`
- `minio`
- `frontend`

### Kubernetes

- API deployment with horizontal scaling
- worker deployment for asynchronous jobs
- ingress for external routing
- secrets and config maps for runtime config
- managed Postgres, object storage, and vector database in production

## Scalability plan

### For 1,000+ users and 100,000+ documents

- background ingestion with queue-based fan-out
- separate read and write pools for PostgreSQL
- Qdrant sharding and payload indexes
- application-level caching where needed
- document parsing workers isolated from API pods
- report generation offloaded to async workers

## Security considerations

- JWT auth is implemented as the baseline, but production should add refresh tokens and revocation.
- Add RBAC beyond `user` and `admin`, especially workspace membership roles.
- Enforce object-level authorization for all workspace assets.
- Encrypt secrets in deployment systems and avoid shipping `.env` files.
- Add malware scanning and file-type verification on uploads.
- Add audit logging for auth, connector syncs, exports, and agent access to sources.

## Observability

- LangSmith for traces, tool usage, and prompt telemetry.
- Structured application logs with request IDs and run IDs.
- Metrics for ingestion throughput, retrieval latency, reranker latency, and report generation time.
- Evaluation datasets for retrieval quality and citation correctness.

## Cost optimization strategy

- Use tiered storage in MinIO or cloud object storage for raw files and exports.
- Cache embeddings and only re-embed changed chunks.
- Run smaller rerankers and models by default; escalate to premium models only for deep research.
- Batch ingestion jobs and connector sync jobs.
- Move inactive workspaces to cold retrieval tiers when needed.

## Roadmap

### Development roadmap

1. Swap the transitional in-memory retrieval service for Qdrant plus BM25 persistence.
2. Replace placeholder binary extractors with parser adapters for PDF, DOCX, and PPTX.
3. Implement background workers with a database-backed queue or managed task system.
4. Add Alembic migrations.
5. Add LangGraph execution engine and LangSmith instrumentation.
6. Add true web search integration and configurable LLM providers.
7. Add report export jobs for PDF and DOCX.

### Production roadmap

1. Add workspace membership and tenant boundaries.
2. Add connector auth flows and sync orchestration.
3. Add SSO, refresh tokens, and audit logs.
4. Add evaluation pipelines and regression tests for retrieval quality.
5. Add autoscaling policies and managed infrastructure.

## Local run

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Full stack with containers

```bash
docker compose up --build
```

## Notes on current implementation

- This is now a production-oriented foundation, not a toy single-file QA app.
- The backend API, schema model, and deployment assets are real and runnable.
- Some advanced runtime pieces are still intentionally transitional inside this repo version:
  - Qdrant execution path is not wired yet even though the architecture and dependencies are prepared.
  - LangGraph is represented as the agent design contract, not a full graph runtime.
  - Web search and MCP tools are exposed as pluggable interfaces with placeholder implementations.

That means the project is now structurally ready for enterprise features, while the next iterations should focus on swapping the remaining placeholder services for their production integrations.
