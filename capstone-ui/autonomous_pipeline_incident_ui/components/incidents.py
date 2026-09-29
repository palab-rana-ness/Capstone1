import reflex as rx
from autonomous_pipeline_incident_ui.models import IncidentRecord
from autonomous_pipeline_incident_ui.states.incident_state import IncidentState
from autonomous_pipeline_incident_ui.components.incident_badges import status_badge, severity_badge
from autonomous_pipeline_incident_ui.components.dashboard import table_header, empty_panel, section_heading


def filter_select(
    label: str,
    value: str,
    options: list[str],
    handler: rx.event.EventType,
    all_label: str = "",
) -> rx.Component:
    return rx.el.div(
        rx.el.label(
            label,
            html_for=label,
            class_name="mb-2 block text-[9px] font-semibold uppercase tracking-wider text-zinc-500",
        ),
        rx.el.div(
            rx.el.select(
                rx.cond(all_label != "", rx.el.option(all_label, value="ALL")),
                rx.foreach(
                    options,
                    lambda option: rx.el.option(
                        option.lower().split("_").join(" "), value=option
                    ),
                ),
                id=label,
                value=value,
                on_change=handler,
                class_name="w-full appearance-none rounded-md border border-white/10 bg-[#202226] py-2.5 pl-3 pr-8 text-xs capitalize text-zinc-200 outline-hidden focus:border-amber-400/60",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-3 h-3 w-3 text-zinc-500",
            ),
            class_name="relative",
        ),
        class_name="min-w-0",
    )


def filters() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.label(
                "SEARCH INCIDENTS",
                html_for="incident-search",
                class_name="mb-2 block text-[9px] font-semibold tracking-wider text-zinc-500",
            ),
            rx.el.div(
                rx.icon(
                    "search",
                    class_name="absolute left-3 top-3 h-3.5 w-3.5 text-zinc-500",
                ),
                rx.el.input(
                    id="incident-search",
                    placeholder="Search ID, pipeline, tenant or platform…",
                    default_value=IncidentState.search_query,
                    on_change=IncidentState.set_query.debounce(300),
                    class_name="w-full rounded-md border border-white/10 bg-[#202226] py-2.5 pl-9 pr-3 text-xs text-zinc-200 placeholder:text-zinc-600 outline-hidden focus:border-amber-400/60",
                ),
                class_name="relative",
            ),
            class_name="sm:col-span-2 xl:col-span-2",
        ),
        filter_select(
            "Status",
            IncidentState.status_filter,
            IncidentState.statuses,
            IncidentState.set_status,
            "All statuses",
        ),
        filter_select(
            "Severity",
            IncidentState.severity_filter,
            IncidentState.severities,
            IncidentState.set_severity,
            "All severities",
        ),
        filter_select(
            "Sort",
            IncidentState.selected_sort,
            IncidentState.sorts,
            IncidentState.set_sort,
        ),
        class_name="grid grid-cols-1 gap-4 border-b border-white/10 p-5 sm:grid-cols-2 xl:grid-cols-5",
    )


def incident_row(incident: IncidentRecord) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            incident.id,
            class_name="whitespace-nowrap px-5 py-4 font-mono text-xs text-zinc-200",
        ),
        rx.el.td(
            incident.pipeline,
            class_name="min-w-44 px-4 py-4 text-xs text-zinc-300",
        ),
        rx.el.td(
            incident.tenant,
            class_name="whitespace-nowrap px-4 py-4 text-xs text-zinc-300",
        ),
        rx.el.td(
            incident.platform, class_name="px-4 py-4 text-xs text-zinc-300"
        ),
        rx.el.td(severity_badge(incident.severity), class_name="px-4 py-4"),
        rx.el.td(
            status_badge(
                rx.cond(
                    (incident.status == "RESOLVED")
                    & ~incident.recovery_confirmed,
                    "RECOVERY_UNCONFIRMED",
                    incident.status,
                )
            ),
            class_name="px-4 py-4",
        ),
        rx.el.td(
            incident.detected,
            class_name="whitespace-nowrap px-5 py-4 font-mono text-[10px] text-zinc-500",
        ),
        rx.el.td(
            rx.el.button(
                "View",
                rx.icon("arrow-up-right", class_name="h-3 w-3"),
                on_click=IncidentState.select_incident(incident.id),
                disabled=IncidentState.busy | IncidentState.selecting,
                aria_label=f"View incident {incident.id}",
                title="Open incident evidence and remediation controls",
                class_name="inline-flex items-center gap-1.5 rounded-sm px-2 py-1 text-xs text-amber-300 transition-colors hover:bg-amber-400/10 hover:text-amber-200 focus-visible:outline-2 focus-visible:outline-amber-400 disabled:opacity-50",
            ),
            class_name="px-5 py-4",
        ),
        key=incident.id,
        class_name="border-t border-white/5 odd:bg-white/[0.015] transition-colors hover:bg-white/[0.04]",
    )


def incident_table() -> rx.Component:
    return rx.el.div(
        rx.el.table(
            rx.el.thead(
                rx.el.tr(
                    table_header("Incident", "hash"),
                    table_header("Pipeline", "workflow"),
                    table_header("Tenant", "building-2"),
                    table_header("Platform", "layers"),
                    table_header("Severity", "signal"),
                    table_header("Status", "circle-dot"),
                    table_header("Time", "clock"),
                    table_header("Action", "arrow-up-right"),
                )
            ),
            rx.el.tbody(
                rx.foreach(IncidentState.visible_incidents, incident_row)
            ),
            class_name="table-auto w-full",
            aria_label="Authorized incidents",
        ),
        class_name="w-full overflow-x-auto",
        tab_index=0,
    )


def loading_rows() -> rx.Component:
    return rx.el.div(
        rx.foreach(
            rx.Var.range(6),
            lambda _: rx.el.div(
                class_name="h-12 animate-pulse rounded-sm bg-zinc-800/60"
            ),
        ),
        class_name="flex min-h-80 flex-col gap-3 p-5",
        aria_busy=True,
        aria_label="Loading incidents",
    )


def incident_results() -> rx.Component:
    return rx.el.section(
        section_heading(
            "01", "Incident register", "BACKEND-AUTHORIZED RESULTS"
        ),
        filters(),
        rx.cond(
            IncidentState.busy,
            loading_rows(),
            rx.cond(
                IncidentState.error_kind != "",
                rx.el.div(
                    rx.icon(
                        "triangle-alert", class_name="h-7 w-7 text-amber-400"
                    ),
                    rx.el.h2(
                        IncidentState.error_title,
                        class_name="mt-4 text-lg font-semibold text-zinc-100",
                    ),
                    rx.el.p(
                        IncidentState.error_description,
                        class_name="mt-2 max-w-lg text-xs leading-6 text-zinc-400",
                    ),
                    rx.el.button(
                        "Retry connection",
                        rx.icon("arrow-right", class_name="h-4 w-4"),
                        on_click=IncidentState.refresh,
                        disabled=IncidentState.busy,
                        class_name="mt-5 flex items-center gap-2 rounded-md bg-amber-400 px-4 py-2 text-xs font-semibold text-zinc-950 hover:bg-amber-300 disabled:opacity-50",
                    ),
                    role="alert",
                    class_name="p-8",
                ),
                rx.cond(
                    IncidentState.loaded,
                    rx.cond(
                        IncidentState.raw_incidents.length() == 0,
                        empty_panel(
                            "No authorized incidents",
                            "The service returned no incidents for this tenant and platform.",
                        ),
                        rx.cond(
                            IncidentState.visible_incidents.length() == 0,
                            rx.el.div(
                                empty_panel(
                                    "No filter matches",
                                    "Try another search or clear your filters. Only returned incidents are searched.",
                                ),
                                rx.el.button(
                                    "Clear filters",
                                    on_click=IncidentState.clear_filters,
                                    class_name="mb-6 rounded-md border border-amber-400/30 px-4 py-2 text-xs text-amber-300 hover:bg-amber-400/10",
                                ),
                                class_name="text-center",
                            ),
                            incident_table(),
                        ),
                    ),
                    loading_rows(),
                ),
            ),
        ),
        rx.el.div(
            rx.el.span(
                f"{IncidentState.visible_incidents.length()} shown / {IncidentState.raw_incidents.length()} returned",
                class_name="text-[10px] text-zinc-500",
            ),
            rx.el.button(
                "Reset filters",
                on_click=IncidentState.clear_filters,
                class_name="text-[10px] text-zinc-400 hover:text-amber-300",
            ),
            class_name="flex items-center justify-between border-t border-white/10 px-5 py-3",
        ),
        class_name="w-full overflow-hidden rounded-md border border-white/10 bg-[#191b1e]",
    )


def incidents_content() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "DETECT / TRIAGE / TRACK",
                    class_name="mb-2 text-[9px] font-medium tracking-[0.2em] text-amber-400",
                ),
                rx.el.h1(
                    "INCIDENT WORKSPACE",
                    class_name="font-['Barlow_Condensed'] text-4xl font-semibold tracking-wide text-zinc-100 sm:text-5xl",
                ),
                rx.el.p(
                    "Every signal, in context. Track the latest confirmed incident state.",
                    class_name="mt-3 text-xs text-zinc-500",
                ),
            ),
            rx.el.button(
                rx.icon(
                    "refresh-cw",
                    class_name=rx.cond(
                        IncidentState.busy,
                        "h-3.5 w-3.5 animate-spin",
                        "h-3.5 w-3.5",
                    ),
                ),
                rx.cond(
                    IncidentState.refreshing, "Refreshing…", "Refresh incidents"
                ),
                on_click=IncidentState.refresh,
                disabled=IncidentState.busy | IncidentState.selecting,
                class_name="flex items-center gap-2 rounded-md border border-white/15 bg-[#202226] px-4 py-2.5 text-xs font-medium text-zinc-200 transition-colors hover:border-amber-400/50 hover:text-amber-300 disabled:cursor-wait disabled:opacity-50",
            ),
            class_name="flex flex-wrap items-center justify-between gap-5 py-8",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("shield-check", class_name="h-4 w-4 text-amber-300"),
                rx.el.span(
                    IncidentState.feedback,
                    class_name="text-[10px] text-zinc-400",
                ),
                rx.el.span(
                    IncidentState.updated_at,
                    class_name="font-mono text-[10px] text-zinc-500",
                ),
                class_name="flex flex-wrap items-center gap-3",
                role="status",
                aria_live="polite",
            ),
            rx.cond(
                IncidentState.demo,
                rx.el.div(
                    rx.el.span(
                        "DEVELOPMENT DEMO",
                        class_name="text-[9px] tracking-wider text-amber-300",
                    ),
                    rx.el.button(
                        "Simulate new detection",
                        rx.icon("radar", class_name="h-3 w-3"),
                        on_click=IncidentState.new_detection,
                        disabled=IncidentState.busy | IncidentState.selecting,
                        class_name="flex items-center gap-2 rounded-sm border border-white/10 px-3 py-2 text-[10px] text-zinc-300 hover:text-amber-300 disabled:opacity-50",
                    ),
                    class_name="flex items-center gap-3",
                ),
            ),
            class_name="mb-5 flex flex-wrap items-center justify-between gap-3",
        ),
        incident_results(),
        rx.el.footer(
            "Scoped by tenant. Reported by service. Search and filters never expand access.",
            class_name="py-6 text-[9px] text-zinc-600",
        ),
        class_name="w-full",
    )
