"""LangGraph StateGraph wiring for the incident diagnosis workflow."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    build_response,
    diagnose_failure,
    fetch_logs,
    generate_remediation,
    resolve_adapter,
    retrieve_similar_incidents,
    store_incident_memory,
    validate_incident,
    validate_remediation,
    validate_trigger,
)
from app.graph.state import AgentState


def build_incident_diagnosis_graph():
    """Build and compile the incident-diagnosis LangGraph.

    Graph shape:
        START -> validate_trigger -> resolve_adapter -> fetch_logs ->
        validate_incident -> retrieve_similar_incidents -> diagnose_failure ->
        generate_remediation -> validate_remediation ->
        store_incident_memory -> build_response -> END
    """
    graph = StateGraph(AgentState)

    graph.add_node("validate_trigger", validate_trigger)
    graph.add_node("resolve_adapter", resolve_adapter)
    graph.add_node("fetch_logs", fetch_logs)
    graph.add_node("validate_incident", validate_incident)
    graph.add_node("retrieve_similar_incidents", retrieve_similar_incidents)
    graph.add_node("diagnose_failure", diagnose_failure)
    graph.add_node("generate_remediation", generate_remediation)
    graph.add_node("validate_remediation", validate_remediation)
    graph.add_node("store_incident_memory", store_incident_memory)
    graph.add_node("build_response", build_response)

    graph.add_edge(START, "validate_trigger")
    graph.add_edge("validate_trigger", "resolve_adapter")
    graph.add_edge("resolve_adapter", "fetch_logs")
    graph.add_edge("fetch_logs", "validate_incident")
    graph.add_edge("validate_incident", "retrieve_similar_incidents")
    graph.add_edge("retrieve_similar_incidents", "diagnose_failure")
    graph.add_edge("diagnose_failure", "generate_remediation")
    graph.add_edge("generate_remediation", "validate_remediation")
    graph.add_edge("validate_remediation", "store_incident_memory")
    graph.add_edge("store_incident_memory", "build_response")
    graph.add_edge("build_response", END)

    return graph.compile()


_compiled_graph = None


def get_incident_diagnosis_graph():
    """Return a process-wide cached compiled graph instance."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_incident_diagnosis_graph()
    return _compiled_graph
