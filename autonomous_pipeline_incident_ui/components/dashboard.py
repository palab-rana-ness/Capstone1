import reflex as rx
import reflex_xy
from autonomous_pipeline_incident_ui.models import Metric, Incident, Pipeline
from autonomous_pipeline_incident_ui.states.dashboard_state import DashboardState
from autonomous_pipeline_incident_ui.states.scope_state import ScopeState
from autonomous_pipeline_incident_ui.components.incident_badges import status_badge, severity_badge


def section_heading(number: str, title: str, caption: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                number, class_name="font-mono text-[10px] text-amber-400"
            ),
            rx.el.h2(
                title,
                class_name="font-['Barlow_Condensed'] text-xl font-semibold uppercase tracking-wider text-zinc-100",
            ),
            class_name="flex items-center gap-3",
        ),
        rx.el.span(caption, class_name="text-[10px] text-zinc-500"),
        class_name="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-5 py-4",
    )


def metric_tile(metric: Metric) -> rx.Component:
    return rx.el.div(
        rx.el.p(
            metric.label, class_name="text-[10px] font-medium text-zinc-400"
        ),
        rx.el.p(
            metric.value,
            class_name=rx.cond(
                metric.label == "Awaiting approval",
                "my-3 font-['Barlow_Condensed'] text-4xl font-medium tracking-tight text-amber-300",
                "my-3 font-['Barlow_Condensed'] text-4xl font-medium tracking-tight text-zinc-100",
            ),
        ),
        rx.el.p(metric.note, class_name="text-[9px] leading-4 text-zinc-500"),
        class_name="w-full border border-white/10 bg-[#1b1d20] px-4 py-4 rounded-md",
    )


def pipeline_row(pipeline: Pipeline) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("workflow", class_name="h-4 w-4 text-zinc-500"),
                rx.el.span(
                    pipeline.name,
                    class_name="text-xs font-medium text-zinc-200",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.span(
                f"{pipeline.health:.1f}%",
                class_name=rx.cond(
                    pipeline.health < 90,
                    "font-mono text-xs text-amber-300",
                    "font-mono text-xs text-zinc-300",
                ),
            ),
            class_name="flex items-center justify-between gap-3",
        ),
        rx.el.progress(
            value=pipeline.health,
            max=100,
            aria_label=f"{pipeline.name} health",
            class_name=rx.cond(
                pipeline.health < 90,
                "my-3 block h-1.5 w-full overflow-hidden rounded-none bg-zinc-800 [&::-webkit-progress-bar]:bg-zinc-800 [&::-webkit-progress-value]:bg-amber-400 [&::-moz-progress-bar]:bg-amber-400",
                "my-3 block h-1.5 w-full overflow-hidden rounded-none bg-zinc-800 [&::-webkit-progress-bar]:bg-zinc-800 [&::-webkit-progress-value]:bg-zinc-400 [&::-moz-progress-bar]:bg-zinc-400",
            ),
        ),
        rx.el.div(
            rx.el.span(pipeline.detail, class_name="text-[10px] text-zinc-500"),
            rx.el.span(
                pipeline.status,
                class_name=rx.cond(
                    pipeline.health < 90,
                    "text-[10px] text-amber-300",
                    "text-[10px] text-zinc-400",
                ),
            ),
            class_name="flex items-center justify-between gap-2",
        ),
        class_name="border-b border-white/5 py-4 last:border-0",
    )


def pipeline_panel() -> rx.Component:
    return rx.el.section(
        section_heading("01", "Pipeline health", "CURRENT SNAPSHOT"),
        rx.cond(
            DashboardState.pipelines.length() > 0,
            rx.el.div(
                rx.foreach(DashboardState.pipelines, pipeline_row),
                class_name="px-5 pb-2",
            ),
            empty_panel(
                "No pipelines in this workspace",
                "Pipeline health will appear when the service reports telemetry.",
            ),
        ),
        rx.cond(
            DashboardState.pipelines.length() > 0,
            rx.el.details(
                rx.el.summary(
                    "Explore health comparison",
                    class_name="cursor-pointer px-5 py-3 text-[10px] text-zinc-400 transition-colors hover:text-amber-300",
                ),
                rx.el.div(
                    reflex_xy.chart(
                        reflex_xy.bar("pipeline", "health", color="#d99b22"),
                        reflex_xy.x_axis(label="Pipeline"),
                        reflex_xy.y_axis(label="Health (%)"),
                        reflex_xy.modebar(False),
                        reflex_xy.interaction_config(navigation=False),
                        data=DashboardState.health_chart,
                        height="260px",
                        class_name="w-full min-w-[300px]",
                    ),
                    class_name="mx-4 mb-4 overflow-x-auto rounded-sm bg-zinc-100 p-3 text-zinc-900",
                ),
                class_name="border-t border-white/10",
            ),
        ),
        class_name="min-w-0 rounded-md border border-white/10 bg-[#191b1e]",
    )


def empty_panel(title: str, description: str) -> rx.Component:
    return rx.el.div(
        rx.icon("scan-line", class_name="mb-3 h-7 w-7 text-zinc-500"),
        rx.el.p(title, class_name="text-sm font-medium text-zinc-200"),
        rx.el.p(
            description,
            class_name="mt-2 max-w-md text-center text-xs leading-5 text-zinc-500",
        ),
        class_name="flex min-h-44 flex-col items-center justify-center px-5 py-8",
    )


def briefing_panel() -> rx.Component:
    return rx.el.section(
        section_heading("02", "Operations brief", "OVERSIGHT"),
        rx.el.div(
            rx.el.div(
                rx.icon("activity", class_name="h-5 w-5 text-amber-300"),
                rx.el.span(
                    "WORKSPACE PULSE",
                    class_name="text-[9px] tracking-[0.15em] text-zinc-500",
                ),
                class_name="flex items-center gap-3",
            ),
            rx.el.h3(
                DashboardState.summary,
                class_name="mt-5 font-['Barlow_Condensed'] text-3xl font-medium leading-tight text-zinc-100",
            ),
            rx.el.p(
                "A consolidated view of detection, response, and recovery. Statuses reflect the latest confirmed service response.",
                class_name="mt-4 text-xs leading-6 text-zinc-400",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.span("Reporting window", class_name="text-zinc-500"),
                    rx.el.span(
                        DashboardState.window, class_name="text-zinc-200"
                    ),
                    class_name="flex justify-between gap-2",
                ),
                rx.el.div(
                    rx.el.span("Platform", class_name="text-zinc-500"),
                    rx.el.span(
                        ScopeState.platform_label, class_name="text-zinc-200"
                    ),
                    class_name="flex justify-between gap-2",
                ),
                rx.el.div(
                    rx.el.span("Last synchronized", class_name="text-zinc-500"),
                    rx.el.span(
                        DashboardState.updated_at,
                        class_name="font-mono text-zinc-200",
                    ),
                    class_name="flex justify-between gap-2",
                ),
                class_name="mt-7 flex flex-col gap-4 border-t border-white/10 pt-5 text-[11px]",
            ),
            rx.el.div(
                rx.icon(
                    "shield-check", class_name="h-4 w-4 shrink-0 text-amber-300"
                ),
                rx.el.p(
                    "Human oversight stays in the loop. Approval and execution are managed by the service.",
                    class_name="text-[10px] leading-5 text-zinc-400",
                ),
                class_name="mt-6 flex gap-3 border-l-2 border-amber-400/60 bg-amber-400/5 p-3",
            ),
            class_name="p-5",
        ),
        class_name="rounded-md border border-white/10 bg-[#191b1e]",
    )


def incident_row(incident: Incident) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            incident.id,
            class_name="whitespace-nowrap px-5 py-4 font-mono text-xs text-zinc-200",
        ),
        rx.el.td(
            incident.pipeline,
            class_name="whitespace-nowrap px-4 py-4 text-xs text-zinc-300",
        ),
        rx.el.td(
            incident.tenant,
            class_name="whitespace-nowrap px-4 py-4 text-xs text-zinc-300",
        ),
        rx.el.td(
            incident.platform,
            class_name="whitespace-nowrap px-4 py-4 text-xs text-zinc-300",
        ),
        rx.el.td(
            severity_badge(incident.severity),
            class_name="px-4 py-4",
        ),
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
            class_name="whitespace-nowrap px-5 py-4 text-right font-mono text-[10px] text-zinc-500",
        ),
        rx.el.td(
            rx.el.button(
                "View",
                rx.icon("arrow-up-right", class_name="h-3 w-3"),
                on_click=DashboardState.select_incident(incident.id),
                disabled=DashboardState.busy | DashboardState.selecting,
                aria_label=f"View incident {incident.id}",
                class_name="inline-flex items-center gap-1.5 rounded-sm px-2 py-1 text-xs text-amber-300 transition-colors hover:bg-amber-400/10 hover:text-amber-200 focus-visible:outline-2 focus-visible:outline-amber-400",
            ),
            class_name="whitespace-nowrap px-5 py-4",
        ),
        class_name="border-t border-white/5 odd:bg-white/[0.015] transition-colors hover:bg-white/[0.04]",
    )


def table_header(label: str, icon: str) -> rx.Component:
    return rx.el.th(
        rx.el.div(
            rx.icon(icon, class_name="h-3 w-3"),
            label,
            class_name="flex items-center gap-2",
        ),
        class_name="whitespace-nowrap px-5 py-3 text-left text-[9px] font-medium uppercase tracking-wider text-zinc-500",
    )


def incidents_panel() -> rx.Component:
    return rx.el.section(
        section_heading("03", "Recent incidents", "LATEST ACTIVITY"),
        rx.cond(
            DashboardState.incidents.length() > 0,
            rx.el.div(
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
                        rx.foreach(DashboardState.incidents, incident_row)
                    ),
                    class_name="table-auto w-full",
                ),
                class_name="w-full overflow-x-auto",
            ),
            empty_panel(
                "No recent incidents",
                "No incidents were returned for the selected tenant and platform.",
            ),
        ),
        class_name="mt-6 overflow-hidden rounded-md border border-white/10 bg-[#191b1e]",
    )


def loading_panel() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(
                "loader-circle",
                class_name="h-4 w-4 animate-spin text-amber-400",
            ),
            rx.el.p(
                DashboardState.feedback, class_name="text-xs text-zinc-400"
            ),
            class_name="mb-5 flex items-center gap-2",
            role="status",
        ),
        rx.el.div(
            rx.foreach(
                rx.Var.range(7),
                lambda _: rx.el.div(
                    class_name="h-32 animate-pulse rounded-md border border-white/5 bg-zinc-800/70"
                ),
            ),
            class_name="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-7",
        ),
        rx.el.div(
            rx.el.div(
                class_name="h-96 animate-pulse rounded-md bg-zinc-800/60 lg:col-span-2"
            ),
            rx.el.div(
                class_name="h-96 animate-pulse rounded-md bg-zinc-800/40"
            ),
            class_name="mt-6 grid gap-6 lg:grid-cols-3",
        ),
        aria_busy=True,
    )


def dashboard_content() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "OBSERVE / UNDERSTAND / RESPOND",
                    class_name="mb-2 text-[9px] font-medium tracking-[0.2em] text-amber-400",
                ),
                rx.el.h1(
                    "OPERATIONS OVERVIEW",
                    class_name="font-['Barlow_Condensed'] text-4xl font-semibold tracking-wide text-zinc-100 sm:text-5xl",
                ),
                rx.el.p(
                    "Every pipeline. Every incident. One operational picture.",
                    class_name="mt-3 text-xs text-zinc-500",
                ),
            ),
            rx.el.button(
                rx.icon(
                    "refresh-cw",
                    class_name=rx.cond(
                        DashboardState.busy,
                        "h-3.5 w-3.5 animate-spin",
                        "h-3.5 w-3.5",
                    ),
                ),
                rx.cond(
                    DashboardState.dashboard_refreshing,
                    "Refreshing…",
                    "Refresh dashboard",
                ),
                on_click=DashboardState.refresh_dashboard,
                disabled=DashboardState.busy,
                class_name="flex items-center gap-2 rounded-md border border-white/15 bg-[#202226] px-4 py-2.5 text-xs font-medium text-zinc-200 transition-colors hover:border-amber-400/50 hover:text-amber-300 disabled:cursor-wait disabled:opacity-50",
            ),
            class_name="flex flex-wrap items-center justify-between gap-5 py-8",
        ),
        rx.cond(
            DashboardState.error_kind != "",
            rx.el.div(
                rx.icon("triangle-alert", class_name="h-8 w-8 text-amber-400"),
                rx.el.h2(
                    DashboardState.error_title,
                    class_name="mt-4 text-lg font-semibold text-zinc-100",
                ),
                rx.el.p(
                    DashboardState.error_description,
                    class_name="mt-2 max-w-lg text-sm leading-6 text-zinc-400",
                ),
                rx.el.button(
                    "Retry connection",
                    rx.icon("arrow-right", class_name="h-4 w-4"),
                    on_click=DashboardState.refresh_dashboard,
                    disabled=DashboardState.busy,
                    class_name="mt-6 flex items-center gap-3 rounded-md bg-amber-400 px-4 py-2.5 text-xs font-semibold text-zinc-950 hover:bg-amber-300",
                ),
                class_name="rounded-md border border-amber-400/20 bg-[#1b1d20] p-8",
                role="alert",
            ),
            rx.cond(
                DashboardState.loaded,
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.span(
                                class_name="h-1.5 w-1.5 rounded-full bg-amber-400"
                            ),
                            rx.el.span(
                                rx.cond(
                                    DashboardState.demo,
                                    "DEVELOPMENT DEMO",
                                    "SERVICE SNAPSHOT",
                                ),
                                class_name="text-[9px] font-semibold tracking-wider text-amber-300",
                            ),
                            rx.el.span(
                                rx.cond(
                                    DashboardState.demo,
                                    "Isolated sample data · no live actions",
                                    "Confirmed data for the selected workspace",
                                ),
                                class_name="text-[10px] text-zinc-500",
                            ),
                            class_name="flex flex-wrap items-center gap-3",
                        ),
                        rx.el.span(
                            DashboardState.window,
                            class_name="text-[10px] text-zinc-500",
                        ),
                        class_name="mb-5 flex items-center justify-between gap-3",
                    ),
                    rx.el.div(
                        rx.foreach(DashboardState.metrics, metric_tile),
                        class_name="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-7",
                    ),
                    rx.el.div(
                        rx.el.div(
                            pipeline_panel(), class_name="min-w-0 lg:col-span-2"
                        ),
                        briefing_panel(),
                        class_name="mt-6 grid items-start gap-6 lg:grid-cols-3",
                    ),
                    incidents_panel(),
                ),
                loading_panel(),
            ),
        ),
        rx.el.footer(
            rx.el.span(
                "SENTINEL / OPERATIONS INTELLIGENCE",
                class_name="text-[8px] tracking-[0.16em] text-zinc-600",
            ),
            rx.el.span(
                "Scoped by tenant. Reported by service.",
                class_name="text-[9px] text-zinc-600",
            ),
            class_name="flex flex-wrap justify-between gap-3 py-6",
        ),
    )
