"""HTTP routes for the incident diagnosis API.

Routes only validate the request, invoke the LangGraph, and shape the
response. No diagnosis logic lives here.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.adapters.registry import UnknownAdapterError
from app.graph.workflow import get_incident_diagnosis_graph
from app.models.incident import IncidentTrigger
from app.models.response import DiagnosisResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["incidents"])


@router.post("/incidents/ai-diagnosis", response_model=DiagnosisResponse)
async def ai_diagnosis(trigger: IncidentTrigger) -> DiagnosisResponse:
    """Kick off the diagnosis graph from a minimal incident trigger.

    The UI no longer supplies logs -- the graph fetches them itself from
    New Relic before running diagnosis and remediation.
    """
    graph = get_incident_diagnosis_graph()

    try:
        result = graph.invoke({"trigger": trigger})
    except UnknownAdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected failure path
        logger.exception("Diagnosis graph failed for incident %s", trigger.incident_id)
        raise HTTPException(status_code=500, detail="Diagnosis failed") from exc

    final_response = result.get("final_response")
    if final_response is None:
        raise HTTPException(status_code=500, detail="Diagnosis did not produce a response")
    return final_response
