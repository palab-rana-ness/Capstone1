# Architecture and Flow Diagram

## Current Architecture (Implemented)

```mermaid
flowchart LR
    subgraph FE[Frontend]
        UI[Reflex UI Dashboard]
    end

    subgraph EX[External Systems]
        NR[New Relic]
        HUMAN[Human Operator]
        LG[LangGraph Agent]
    end

    subgraph BE[FastAPI Backend]
        R[Incident Router<br/>app/routers/incidents.py]
        WF[Workflow Service<br/>app/incident_workflow.py]
        NS[Notification Service<br/>app/services/notification_service.py]
        LS[LangGraph Service<br/>app/services/langgraph_service.py]
        REPO[Incident Repository<br/>app/database/incident_repository.py]
    end

    subgraph DB[PostgreSQL]
        I[(incidents)]
        P[(incident_payloads)]
    end

    NR -->|POST /api/v1/incidents/failures| R
    UI -->|GET /api/v1/incidents| R
    HUMAN -->|POST /api/v1/incidents/:incident_id/agent/invoke| R
    LG -->|POST /api/v1/incidents/:incident_id/agent/result| R

    R --> WF
    WF --> REPO
    REPO --> I
    REPO --> P

    WF --> NS
    WF --> LS
    LS --> LG

    NS -->|Incident detected / failed / resolved| HUMAN
    UI -->|GET /health| R
```

## Incident Workflow (Implemented)

```mermaid
flowchart TD
    A[New Relic sends failure] --> B[FastAPI: POST /api/v1/incidents/failures]
    B --> C[Workflow service strips log fields]
    C --> D[Repository INSERT or UPSERT incident in PostgreSQL]
    D --> E[Notify human: incident detected]

    E --> F[Human reviews incident]
    F --> G[FastAPI: POST /api/v1/incidents/:incident_id/agent/invoke]
    G --> H[Mark status SENDING_TO_AGENT]
    H --> I[Invoke LangGraph service]

    I --> J[FastAPI: POST /api/v1/incidents/:incident_id/agent/result]
    J --> K{Validation outcome}

    K -->|FAILED| L[Repository UPDATE status ESCALATED]
    L --> M[Notify human: remediation failed]

    K -->|SUCCEEDED + validated_resolved=false| N[Repository UPDATE status VALIDATING]
    N --> O[Notify human: validation pending]

    K -->|SUCCEEDED + validated_resolved=true| P[Repository DELETE incident row + payload row]
    P --> Q[Notify human: error resolved]
```

## Endpoint Surface (Kept)

- GET /health
- POST /api/v1/incidents/failures
- GET /api/v1/incidents
- POST /api/v1/incidents/{incident_id}/agent/invoke
- POST /api/v1/incidents/{incident_id}/agent/result

## Service Layer and Responsibilities

- Router layer: accepts API requests and returns standardized response envelope.
- Workflow service: orchestrates business flow and status transitions.
- Repository layer: performs all PostgreSQL operations with SQLAlchemy ORM.
- Notification service: emits human-facing status notifications.
- LangGraph service: triggers the external remediation agent.
