import reflex as rx
from autonomous_pipeline_incident_ui.states.scope_state import ScopeState
from autonomous_pipeline_incident_ui.states.dashboard_state import DashboardState
from autonomous_pipeline_incident_ui.states.incident_state import IncidentState
from autonomous_pipeline_incident_ui.states.detail_state import DetailState
from autonomous_pipeline_incident_ui.states.config_state import ConfigState


def navigation(active: str = "Dashboard") -> rx.Component:
    return rx.el.nav(
        rx.el.a(
            rx.icon("layout-dashboard", class_name="h-4 w-4"),
            "Dashboard",
            href="/",
            class_name=rx.cond(
                active == "Dashboard",
                "flex items-center gap-3 border-l-2 border-amber-400 bg-amber-400/10 px-5 py-3 text-sm font-medium text-amber-300",
                "flex items-center gap-3 border-l-2 border-transparent px-5 py-3 text-sm text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-100",
            ),
            aria_current=rx.cond(active == "Dashboard", "page", "false"),
        ),
        rx.el.a(
            rx.icon("list-filter", class_name="h-4 w-4"),
            "Incidents",
            rx.icon(
                "arrow-up-right", class_name="ml-auto h-3 w-3 text-zinc-600"
            ),
            href="/incidents",
            class_name=rx.cond(
                active == "Incidents",
                "flex items-center gap-3 border-l-2 border-amber-400 bg-amber-400/10 px-5 py-3 text-sm font-medium text-amber-300",
                "flex items-center gap-3 border-l-2 border-transparent px-5 py-3 text-sm text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-100",
            ),
            aria_current=rx.cond(active == "Incidents", "page", "false"),
            title="Incidents workspace",
        ),
        rx.el.a(
            rx.icon("sliders-horizontal", class_name="h-4 w-4"),
            "Configuration",
            href="/configuration",
            class_name=rx.cond(
                active == "Configuration",
                "flex items-center gap-3 border-l-2 border-amber-400 bg-amber-400/10 px-5 py-3 text-sm font-medium text-amber-300",
                "flex items-center gap-3 border-l-2 border-transparent px-5 py-3 text-sm text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-100",
            ),
            aria_current=rx.cond(active == "Configuration", "page", "false"),
            title="Configuration workspace",
        ),
        class_name="flex flex-col gap-1",
    )


def scope_controls() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.label(
                "TENANT",
                html_for="tenant",
                class_name="text-[10px] font-semibold tracking-[0.16em] text-zinc-500",
            ),
            rx.el.div(
                rx.icon("building-2", class_name="h-4 w-4 text-zinc-500"),
                rx.el.select(
                    rx.el.option("Select tenant", value="", disabled=True),
                    rx.foreach(
                        ScopeState.tenants,
                        lambda item: rx.el.option(item.label, value=item.id),
                    ),
                    id="tenant",
                    value=ScopeState.tenant_id,
                    on_change=ScopeState.switch_tenant,
                    disabled=DashboardState.busy
                    | IncidentState.busy
                    | DetailState.busy
                    | ConfigState.busy,
                    class_name="w-full appearance-none bg-transparent py-1 pr-6 text-sm text-zinc-200 outline-hidden disabled:cursor-wait [&>option]:bg-zinc-900",
                ),
                rx.icon(
                    "chevron-down",
                    class_name="pointer-events-none absolute right-0 h-3 w-3 text-zinc-500",
                ),
                class_name="relative flex items-center gap-2",
            ),
            class_name="min-w-32 flex-1",
        ),
        rx.el.div(class_name="h-8 w-px bg-white/10"),
        rx.el.div(
            rx.el.label(
                "PLATFORM",
                html_for="platform",
                class_name="text-[10px] font-semibold tracking-[0.16em] text-zinc-500",
            ),
            rx.el.div(
                rx.icon("layers", class_name="h-4 w-4 text-amber-400"),
                rx.el.select(
                    rx.el.option("Select platform", value="", disabled=True),
                    rx.foreach(
                        ScopeState.platforms,
                        lambda item: rx.el.option(item.label, value=item.id),
                    ),
                    id="platform",
                    value=ScopeState.platform_id,
                    on_change=ScopeState.switch_platform,
                    disabled=DashboardState.busy
                    | IncidentState.busy
                    | DetailState.busy
                    | ConfigState.busy,
                    class_name="w-full appearance-none bg-transparent py-1 pr-6 text-sm text-zinc-200 outline-hidden disabled:cursor-wait [&>option]:bg-zinc-900",
                ),
                rx.icon(
                    "chevron-down",
                    class_name="pointer-events-none absolute right-0 h-3 w-3 text-zinc-500",
                ),
                class_name="relative flex items-center gap-2",
            ),
            class_name="min-w-28 flex-1",
        ),
        class_name="flex w-full flex-wrap items-center gap-5 rounded-md border border-white/10 bg-[#1b1d20] px-4 py-2 sm:w-auto",
    )


def shell(content: rx.Component, active: str = "Dashboard") -> rx.Component:
    return rx.el.div(
        rx.el.header(
            rx.el.a(
                rx.el.div(
                    rx.icon("radar", class_name="h-6 w-6"),
                    class_name="flex h-9 w-9 items-center justify-center rounded-md bg-amber-400 text-zinc-950",
                ),
                rx.el.div(
                    rx.el.span(
                        "SENTINEL",
                        class_name="font-['Barlow_Condensed'] text-2xl font-semibold tracking-[0.16em] text-zinc-100",
                    ),
                    rx.el.p(
                        "AUTONOMOUS OPERATIONS",
                        class_name="text-[8px] tracking-[0.2em] text-zinc-500",
                    ),
                ),
                href="/",
                class_name="flex items-center gap-3",
            ),
            rx.el.div(
                rx.el.span(
                    "OPERATIONS CONTROL ROOM",
                    class_name="hidden text-[10px] tracking-[0.2em] text-zinc-500 lg:block",
                ),
                rx.el.span(
                    "01",
                    class_name="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-zinc-800 text-xs text-zinc-300",
                ),
                class_name="flex items-center gap-6",
            ),
            class_name="flex h-[76px] shrink-0 items-center justify-between border-b border-white/10 bg-[#17191c] px-5 lg:px-7",
        ),
        rx.el.div(
            rx.el.aside(
                rx.el.p(
                    "WORKSPACE",
                    class_name="px-5 pb-4 pt-8 text-[9px] font-semibold tracking-[0.2em] text-zinc-600",
                ),
                navigation(active),
                rx.el.div(
                    rx.icon(
                        "shield-check", class_name="mb-3 h-5 w-5 text-zinc-500"
                    ),
                    rx.el.p(
                        "Built for oversight.",
                        class_name="text-xs text-zinc-300",
                    ),
                    rx.el.p(
                        "Autonomous response.\nHuman control.",
                        class_name="mt-2 whitespace-pre-line text-[11px] leading-5 text-zinc-500",
                    ),
                    class_name="mx-5 mt-auto border-t border-white/10 py-6",
                ),
                class_name="hidden w-56 shrink-0 flex-col border-r border-white/10 bg-[#17191c] md:flex",
            ),
            rx.el.main(
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Workspace", class_name="text-zinc-500"),
                        rx.icon(
                            "chevron-right", class_name="h-3 w-3 text-zinc-600"
                        ),
                        rx.el.span(active, class_name="text-zinc-300"),
                        class_name="flex items-center gap-2 text-xs",
                    ),
                    scope_controls(),
                    class_name="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5",
                ),
                rx.el.div(navigation(active), class_name="mt-4 md:hidden"),
                content,
                class_name="w-full min-w-0 flex-1 overflow-y-auto px-5 py-5 lg:px-8 lg:py-6",
            ),
            class_name="flex min-h-0 flex-1",
        ),
        class_name="flex h-dvh w-full flex-col overflow-hidden bg-[#121416] font-['Inter'] text-zinc-200 selection:bg-amber-400/30",
    )
