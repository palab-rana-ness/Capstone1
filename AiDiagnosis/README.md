# AI Diagnosis Agent

Agentic backend for autonomous data-pipeline incident diagnosis. This service
receives a failed-incident JSON payload (already assembled by the Reflex UI),
runs it through a LangGraph workflow, and returns a structured diagnosis and
remediation recommendation.

This repository intentionally does **not** implement the Reflex UI, incident
storage in PostgreSQL, pipeline monitoring/failure detection, Spark/Synapse
cluster connectors, Airflow integration, or remediation execution. It only
diagnoses and recommends.

## Architecture

```
FastAPI (app/api/routes.py)
      │
      ▼
LangGraph (app/graph/workflow.py)
  validate_incident
      │
      ▼
  resolve_adapter ───────► PipelineAdapter (SparkAdapter / SynapseAdapter)
      │
      ▼
  retrieve_similar_incidents ──► IncidentMemoryRepository (Chroma)
      │
      ▼
  diagnose_failure ───────► diagnosis_service (LLM, structured output)
      │
      ▼
  generate_remediation ───► remediation_service (LLM, structured output)
      │
      ▼
  validate_remediation (deterministic safety checks)
      │
      ▼
  store_incident_memory ──► IncidentMemoryRepository (Chroma)
      │
      ▼
  build_response
```

The graph only depends on the generic `Incident` model and the abstract
`PipelineAdapter` / `IncidentMemoryRepository` interfaces. Spark is the fully
implemented adapter; Synapse is a minimal prototype that proves the graph is
technology-independent.

## Multi-tenancy

Every incident carries a `tenant_id`. Chroma similarity search always filters
by `tenant_id` as part of the query itself (never as a post-hoc filter), so
one tenant can never retrieve another tenant's historical incidents. Matching
`adapter` is a soft preference used to rank results, not a hard filter.

## Running locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in GROQ_API_KEY
python -m scripts.seed_data   # optional: seed demo historical incidents
uvicorn app.main:app --reload
```

- `GET /health` — liveness check
- `POST /api/v1/incidents/ai-diagnosis` — run the diagnosis graph on an
  `Incident` JSON payload (see the project prompt for an example).

## Testing

```powershell
pytest
```

Tests do not call a real LLM or a real Chroma persistence path shared with the
app: LLM calls are replaced with deterministic fakes, and Chroma tests use a
temporary directory per test.

## Project layout

See `app/`, `tests/`, and `scripts/seed_data.py`. Key extension points:

- Add a new pipeline technology: implement `PipelineAdapter` in
  `app/adapters/`, then register it in `app/adapters/registry.py`. No changes
  to `app/graph/` are required.
- Swap the incident memory backend: implement `IncidentMemoryRepository` in
  `app/memory/`.
- Swap the LLM provider: `app/services/llm_client.py` builds a LangChain
  `ChatGroq` client from `GROQ_API_KEY`/`GROQ_MODEL`.
