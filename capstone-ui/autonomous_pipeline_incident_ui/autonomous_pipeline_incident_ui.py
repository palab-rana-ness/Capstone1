import reflex as rx
from autonomous_pipeline_incident_ui.components.shell import shell
from autonomous_pipeline_incident_ui.components.dashboard import dashboard_content
from autonomous_pipeline_incident_ui.states.dashboard_state import DashboardState
from autonomous_pipeline_incident_ui.components.incidents import incidents_content
from autonomous_pipeline_incident_ui.states.incident_state import IncidentState
from autonomous_pipeline_incident_ui.components.incident_detail import incident_detail_content
from autonomous_pipeline_incident_ui.states.detail_state import DetailState
from autonomous_pipeline_incident_ui.components.configuration import configuration_content
from autonomous_pipeline_incident_ui.states.config_state import ConfigState


def index() -> rx.Component:
    return shell(dashboard_content())


def incidents() -> rx.Component:
    return shell(incidents_content(), active="Incidents")


def incident_details() -> rx.Component:
    return shell(incident_detail_content(), active="Incidents")


def configuration() -> rx.Component:
    return shell(configuration_content(), active="Configuration")


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(
            rel="preconnect",
            href="https://fonts.gstatic.com",
            cross_origin="",
        ),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Barlow+Condensed:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(
    incident_details,
    route="/incidents/[incident_id]",
    title="Sentinel | Incident control",
    on_load=DetailState.page_load,
)
app.add_page(
    index,
    route="/",
    title="Sentinel | Operations overview",
    on_load=DashboardState.page_load,
)
app.add_page(
    incidents,
    route="/incidents",
    title="Sentinel | Incident workspace",
    on_load=IncidentState.page_load,
)
app.add_page(
    configuration,
    route="/configuration",
    title="Sentinel | Workspace configuration",
    on_load=ConfigState.page_load,
)
