import reflex as rx
from autonomous_pipeline_incident_ui.models import IncidentRecord, DetailEntry, ActionCapability
from autonomous_pipeline_incident_ui.states.detail_state import DetailState
from autonomous_pipeline_incident_ui.components.incident_badges import status_badge, severity_badge
from autonomous_pipeline_incident_ui.components.dashboard import section_heading
from autonomous_pipeline_incident_ui.components.incident_logs import incident_logs_panel


def entry_row(entry: DetailEntry) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                entry.label,
                class_name="text-[10px] font-medium uppercase tracking-wide text-zinc-500",
            ),
            rx.cond(
                entry.timestamp != "",
                rx.el.time(
                    entry.timestamp,
                    class_name="font-mono text-[9px] text-zinc-500",
                ),
            ),
            class_name="flex flex-wrap items-center justify-between gap-2",
        ),
        rx.el.p(
            entry.value,
            class_name="mt-2 whitespace-pre-wrap break-words text-xs leading-6 text-zinc-200",
        ),
        class_name="border-l border-amber-400/30 pl-4 py-2",
    )


def feedback(section: str) -> rx.Component:
    return rx.el.div(
        rx.cond(
            DetailState.errors[section] != "",
            rx.el.p(
                DetailState.errors[section],
                role="alert",
                class_name="rounded-sm border border-amber-400/20 bg-amber-400/5 p-3 text-xs leading-6 text-amber-200",
            ),
            rx.el.p(
                DetailState.section_status[section],
                role="status",
                class_name="text-[10px] text-zinc-500",
            ),
        ),
        rx.el.button(
            rx.icon("refresh-cw", class_name="h-3 w-3"),
            rx.cond(
                DetailState.errors[section] != "",
                "Retry read / reconcile",
                "Refresh",
            ),
            on_click=DetailState.refresh_section(section),
            disabled=DetailState.busy | (DetailState.confirmation != ""),
            class_name="flex shrink-0 items-center gap-2 rounded-sm border border-white/10 bg-[#202226] px-3 py-2 text-[10px] text-zinc-300 hover:border-amber-400/40 hover:text-amber-300 disabled:cursor-wait disabled:opacity-40",
        ),
        class_name="flex flex-wrap items-center justify-between gap-3 border-t border-white/5 px-5 py-3",
    )


def section_panel(number: str, title: str, section: str) -> rx.Component:
    return rx.el.section(
        section_heading(
            number, title, DetailState.sections[section]["progress"]
        ),
        rx.el.div(
            rx.cond(
                DetailState.sections[section]["summary"] != "",
                rx.el.p(
                    DetailState.sections[section]["summary"],
                    class_name="text-sm leading-6 text-zinc-200",
                ),
            ),
            rx.cond(
                (section == "diagnosis")
                & (
                    DetailState.sections[section]["confidence_supplied"]
                    | (DetailState.sections[section]["severity"] != "")
                ),
                rx.el.div(
                    rx.cond(
                        DetailState.sections[section]["confidence_supplied"],
                        rx.el.span(
                            f"Confidence · {DetailState.sections[section]['confidence']:.1f}%",
                            class_name="font-mono text-xs text-amber-300",
                        ),
                    ),
                    rx.cond(
                        DetailState.sections[section]["severity"] != "",
                        severity_badge(
                            DetailState.sections[section]["severity"]
                        ),
                    ),
                    class_name="flex flex-wrap items-center gap-4",
                ),
            ),
            rx.cond(
                DetailState.sections[section]["outcome"] != "",
                rx.el.div(
                    status_badge(DetailState.sections[section]["outcome"]),
                    rx.el.p(
                        "Final outcome reported by the service",
                        class_name="text-[10px] text-zinc-500",
                    ),
                    class_name="flex flex-wrap items-center gap-3 rounded-sm border border-white/10 bg-[#121416] p-4",
                ),
            ),
            rx.cond(
                DetailState.sections[section]["entries"].length() > 0,
                rx.el.div(
                    rx.foreach(
                        DetailState.sections[section]["entries"], entry_row
                    ),
                    class_name="flex flex-col gap-4",
                ),
                rx.cond(
                    DetailState.sections[section]["summary"] == "",
                    rx.el.p(
                        "No records reported by the service.",
                        class_name="text-xs text-zinc-500",
                    ),
                ),
            ),
            rx.cond(
                DetailState.sections[section]["logs"].length() > 0,
                rx.el.div(
                    rx.el.p(
                        "SERVICE LOGS",
                        class_name="mb-3 text-[9px] tracking-widest text-zinc-500",
                    ),
                    rx.el.pre(
                        DetailState.sections[section]["logs"].join("\n"),
                        tab_index=0,
                        class_name="max-h-60 overflow-auto rounded-sm border border-white/10 bg-[#101214] p-4 font-mono text-[10px] leading-6 text-zinc-300",
                    ),
                ),
                rx.cond(
                    (section == "execution") | (section == "evidence"),
                    rx.el.p(
                        "No logs reported.",
                        class_name="text-[10px] text-zinc-500",
                    ),
                ),
            ),
            class_name="flex flex-col gap-5 p-5",
        ),
        feedback(section),
        class_name="min-w-0 rounded-md border border-white/10 bg-[#191b1e]",
    )


def fact(label: str, value: str) -> rx.Component:
    return rx.el.div(
        rx.el.p(
            label,
            class_name="mb-2 text-[9px] uppercase tracking-wider text-zinc-500",
        ),
        rx.el.p(value, class_name="break-words text-xs text-zinc-200"),
        class_name="min-w-0",
    )


def incident_facts(record: IncidentRecord) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h2(record.id, class_name="font-mono text-xl text-amber-300"),
            status_badge(
                rx.cond(
                    (record.status == "RESOLVED") & ~record.recovery_confirmed,
                    "RECOVERY_UNCONFIRMED",
                    record.status,
                )
            ),
            severity_badge(record.severity),
            class_name="mb-6 flex flex-wrap items-center gap-4",
        ),
        rx.el.div(
            fact("Tenant", record.tenant),
            fact("Pipeline", record.pipeline),
            fact("Platform", record.platform),
            fact("Failure time (UTC)", DetailState.detected_at_label),
            class_name="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4",
        ),
        class_name="p-5",
    )


def action_button(capability: ActionCapability) -> rx.Component:
    return rx.el.button(
        rx.icon("shield-check", class_name="h-4 w-4"),
        capability.label,
        on_click=DetailState.choose_action(capability.operation),
        disabled=DetailState.action_busy | (DetailState.confirmation != ""),
        class_name="flex items-center gap-2 rounded-md border border-amber-400/40 bg-amber-400/10 px-4 py-3 text-xs font-medium text-amber-300 hover:bg-amber-400/20 disabled:cursor-wait disabled:opacity-40",
    )


def action_controls() -> rx.Component:
    return rx.el.section(
        section_heading("05", "Human oversight", "BACKEND-AUTHORIZED ACTIONS"),
        rx.el.div(
            rx.el.div(
                rx.icon(
                    "shield-check", class_name="h-5 w-5 shrink-0 text-amber-400"
                ),
                rx.el.div(
                    rx.el.p(
                        DetailState.execution_policy,
                        class_name="text-xs leading-6 text-zinc-200",
                    ),
                    rx.el.p(
                        "Actions and permissions are returned by the service. Execution is never assumed successful.",
                        class_name="mt-2 text-[10px] leading-5 text-zinc-500",
                    ),
                ),
                class_name="flex gap-3",
            ),
            rx.el.label(
                "Analysis reason (optional)",
                html_for="analysis-reason",
                class_name="mt-5 block text-[10px] text-zinc-400",
            ),
            rx.el.input(
                id="analysis-reason",
                placeholder="Add context for the agent…",
                default_value=DetailState.analysis_reason,
                on_change=DetailState.set_analysis_reason.debounce(300),
                disabled=DetailState.busy,
                max_length=2000,
                class_name="mt-2 w-full rounded-md border border-white/10 bg-[#202226] px-3 py-2 text-xs text-zinc-200 focus:border-amber-400/50 outline-hidden",
            ),
            rx.el.p(
                DetailState.lifecycle_message,
                role="status",
                class_name="mt-3 text-xs text-amber-300",
            ),
            rx.cond(
                DetailState.capabilities.length() > 0,
                rx.el.div(
                    rx.foreach(DetailState.capabilities, action_button),
                    class_name="mt-5 flex flex-wrap gap-3",
                ),
                rx.el.p(
                    "No actions currently authorized. Refresh the recommendation to reconcile permissions and status.",
                    class_name="mt-5 text-xs leading-6 text-zinc-500",
                ),
            ),
            rx.cond(
                DetailState.confirmation != "",
                rx.el.div(
                    rx.el.h3(
                        DetailState.confirmation_label,
                        class_name="text-sm font-semibold text-amber-300",
                    ),
                    rx.el.p(
                        DetailState.confirmation_text,
                        class_name="mt-3 text-xs leading-6 text-zinc-200",
                    ),
                    rx.el.div(
                        rx.el.button(
                            "Cancel",
                            on_click=DetailState.cancel_confirmation,
                            disabled=DetailState.busy,
                            class_name="rounded-md border border-white/20 px-4 py-2 text-xs text-zinc-200 hover:bg-white/5",
                        ),
                        rx.el.button(
                            "Confirm action",
                            on_click=DetailState.confirm_action,
                            disabled=DetailState.busy,
                            class_name="rounded-md bg-amber-400 px-4 py-2 text-xs font-semibold text-zinc-950 hover:bg-amber-300 disabled:opacity-40",
                        ),
                        class_name="mt-4 flex flex-wrap gap-3",
                    ),
                    role="alert",
                    class_name="mt-5 rounded-md border border-amber-400/40 bg-amber-400/5 p-4",
                ),
            ),
            rx.cond(
                DetailState.busy,
                rx.el.p(
                    "Operation in progress · controls locked until the service responds…",
                    role="status",
                    class_name="mt-4 animate-pulse text-xs text-amber-300",
                ),
            ),
            class_name="p-5",
        ),
        class_name="rounded-md border border-amber-400/20 bg-[#191b1e]",
    )


def incident_detail_content() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.a(
                rx.icon("arrow-left", class_name="h-3 w-3"),
                "Back to incidents",
                href="/incidents",
                class_name="mb-5 flex w-fit items-center gap-2 text-xs text-zinc-400 hover:text-amber-300",
            ),
            rx.el.p(
                "INVESTIGATE / AUTHORIZE / VERIFY",
                class_name="mb-2 text-[9px] tracking-[0.2em] text-amber-400",
            ),
            rx.el.h1(
                "INCIDENT CONTROL",
                class_name="font-['Barlow_Condensed'] text-4xl font-semibold tracking-wide text-zinc-100 sm:text-5xl",
            ),
            rx.el.p(
                "Evidence-led response. Human oversight. Confirmed recovery.",
                class_name="mt-3 text-xs text-zinc-500",
            ),
            class_name="py-8",
        ),
        rx.cond(
            DetailState.demo,
            rx.el.p(
                "DEVELOPMENT DEMO · synthetic evidence and simulated actions",
                class_name="mb-5 text-[10px] tracking-wide text-amber-300",
            ),
        ),
        rx.el.section(
            rx.foreach(DetailState.records, incident_facts),
            rx.cond(
                (DetailState.records.length() == 0) & DetailState.busy,
                rx.el.div(
                    class_name="m-5 h-24 animate-pulse rounded-sm bg-zinc-800/60"
                ),
            ),
            feedback("facts"),
            class_name="mb-6 rounded-md border border-white/10 bg-[#1b1d20]",
        ),
        rx.cond(
            DetailState.records.length() > 0,
            rx.el.div(
                rx.el.div(
                    section_panel("01", "Evidence & telemetry", "evidence"),
                    section_panel("02", "Diagnosis", "diagnosis"),
                    section_panel("03", "Historical search", "history"),
                    section_panel("08", "Audit timeline", "audit"),
                    class_name="flex min-w-0 flex-col gap-6 lg:col-span-3",
                ),
                rx.el.div(
                    section_panel(
                        "04", "Remediation recommendation", "remediation"
                    ),
                    action_controls(),
                    section_panel("06", "Execution", "execution"),
                    section_panel("07", "Validation & outcome", "validation"),
                    class_name="flex min-w-0 flex-col gap-6 lg:col-span-2",
                ),
                class_name="grid w-full grid-cols-1 items-start gap-6 lg:grid-cols-5",
            ),
        ),
        incident_logs_panel(),
        rx.el.footer(
            "Scoped by tenant · status, evidence, permissions and audit supplied by service",
            class_name="py-6 text-[9px] text-zinc-600",
        ),
        class_name="w-full",
    )
