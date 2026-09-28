import reflex as rx
from autonomous_pipeline_incident_ui.models import LogEntry
from autonomous_pipeline_incident_ui.states.detail_state import DetailState


def log_row(entry: LogEntry) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.el.time(
                entry.timestamp,
                class_name="font-mono text-[10px] text-zinc-400",
            ),
            rx.el.span(
                entry.level,
                class_name="w-fit rounded-sm border border-amber-400/20 bg-amber-400/5 px-2 py-1 text-[9px] text-amber-300",
            ),
            rx.el.span(
                entry.source, class_name="break-all text-[10px] text-zinc-500"
            ),
            class_name="flex flex-wrap items-center gap-3",
        ),
        rx.el.p(
            entry.message,
            class_name="mt-3 whitespace-pre-wrap break-words text-xs leading-6 text-zinc-200",
        ),
        rx.cond(
            entry.fields_json != "{}",
            rx.el.details(
                rx.el.summary(
                    "Structured fields",
                    class_name="cursor-pointer py-3 text-[10px] text-zinc-400 hover:text-amber-300",
                ),
                rx.el.pre(
                    entry.fields_json,
                    class_name="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-sm bg-[#101214] p-4 font-mono text-[10px] leading-5 text-zinc-300",
                ),
            ),
        ),
        class_name="min-w-0 border-t border-white/5 px-5 py-4",
    )


def incident_logs_panel() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.icon("terminal", class_name="h-4 w-4 text-amber-400"),
                rx.el.h2(
                    "Incident logs",
                    class_name="font-['Barlow_Condensed'] text-xl font-semibold uppercase tracking-wider text-zinc-100",
                ),
                class_name="flex items-center gap-3",
            ),
            rx.el.button(
                rx.icon("refresh-cw", class_name="h-3 w-3"),
                rx.cond(
                    DetailState.logs_refreshing, "Refreshing…", "Refresh Logs"
                ),
                on_click=DetailState.refresh_logs,
                disabled=DetailState.logs_loading
                | DetailState.logs_refreshing
                | (DetailState.records.length() == 0)
                | (DetailState.confirmation != ""),
                class_name="flex items-center gap-2 rounded-sm border border-white/10 bg-[#202226] px-3 py-2 text-[10px] text-zinc-300 hover:text-amber-300 disabled:cursor-wait disabled:opacity-40",
            ),
            class_name="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4",
        ),
        rx.cond(
            DetailState.logs_error_kind != "",
            rx.el.p(
                DetailState.logs_error_message,
                role="alert",
                class_name="m-5 rounded-sm border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-200",
            ),
        ),
        rx.cond(
            DetailState.logs_loading,
            rx.el.div(
                class_name="m-5 h-28 animate-pulse rounded-sm bg-zinc-800/60",
                aria_label="Loading incident logs",
            ),
            rx.cond(
                DetailState.logs_empty,
                rx.el.p(
                    "No logs returned for this incident.",
                    class_name="p-5 text-xs text-zinc-500",
                ),
                rx.el.div(
                    rx.foreach(DetailState.log_entries, log_row),
                    class_name="max-h-[640px] overflow-y-auto",
                ),
            ),
        ),
        rx.cond(
            DetailState.logs_refreshing,
            rx.el.p(
                "Waiting for confirmed logs. Previous results remain unchanged.",
                role="status",
                class_name="px-5 pb-4 text-[10px] text-zinc-500",
            ),
        ),
        class_name="mt-6 w-full min-w-0 rounded-md border border-white/10 bg-[#191b1e]",
    )
