import reflex as rx
from autonomous_pipeline_incident_ui.models import ConfigurationResponse
from autonomous_pipeline_incident_ui.states.config_state import ConfigState
from autonomous_pipeline_incident_ui.states.scope_state import ScopeState
from autonomous_pipeline_incident_ui.components.dashboard import section_heading


def rule_control(
    label: str, field: str, value: int, options: list[int], description: str
) -> rx.Component:
    return rx.el.div(
        rx.el.label(
            label,
            html_for=field,
            class_name="mb-2 block text-xs font-medium text-zinc-200",
        ),
        rx.el.div(
            rx.el.select(
                rx.el.option(value, value=value.to_string()),
                rx.foreach(
                    options,
                    lambda option: rx.cond(
                        option != value,
                        rx.el.option(option, value=option.to_string()),
                    ),
                ),
                id=field,
                value=value.to_string(),
                on_change=lambda selected: ConfigState.set_rule(
                    field, selected
                ),
                disabled=~ConfigState.editable,
                class_name="w-full appearance-none rounded-md border border-white/10 bg-[#202226] px-3 py-3 pr-9 text-xs text-zinc-200 outline-hidden focus:border-amber-400 disabled:opacity-50",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-3 h-4 w-4 text-zinc-500",
            ),
            class_name="relative",
        ),
        rx.el.p(
            description, class_name="mt-2 text-[10px] leading-5 text-zinc-500"
        ),
    )


def action_control(action: str) -> rx.Component:
    return rx.el.button(
        rx.icon(
            "check",
            class_name=rx.cond(
                ConfigState.draft.allowed_actions.contains(action),
                "h-4 w-4 text-amber-300",
                "h-4 w-4 text-zinc-700",
            ),
        ),
        action,
        on_click=ConfigState.toggle_action(action),
        disabled=(~ConfigState.editable)
        | (~ConfigState.action_options.contains(action)),
        aria_pressed=ConfigState.draft.allowed_actions.contains(action),
        class_name=rx.cond(
            ConfigState.draft.allowed_actions.contains(action),
            "flex items-center gap-3 rounded-md border border-amber-400/40 bg-amber-400/10 px-4 py-3 text-xs text-amber-300 disabled:opacity-50",
            "flex items-center gap-3 rounded-md border border-white/10 bg-[#202226] px-4 py-3 text-xs text-zinc-400 hover:border-amber-400/30 disabled:opacity-50",
        ),
    )


def configuration_form(record: ConfigurationResponse) -> rx.Component:
    return rx.el.div(
        rx.el.section(
            section_heading(
                "01", "Workspace identity", "SERVICE-CONFIRMED SCOPE"
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.label(
                        "Tenant ID · read only",
                        html_for="config-tenant",
                        class_name="mb-2 block text-[10px] uppercase tracking-wide text-zinc-500",
                    ),
                    rx.el.input(
                        id="config-tenant",
                        default_value=record.tenant_id,
                        key=record.tenant_id,
                        read_only=True,
                        class_name="w-full rounded-md border border-white/10 bg-[#121416] p-3 font-mono text-xs text-zinc-300",
                    ),
                ),
                rx.el.div(
                    rx.el.p(
                        "Platform Type",
                        class_name="mb-2 text-[10px] uppercase tracking-wide text-zinc-500",
                    ),
                    rx.el.p(
                        ScopeState.platform_label,
                        class_name="text-sm text-zinc-200",
                    ),
                    rx.el.p(
                        "Use the shared Platform selector above to change workspace.",
                        class_name="mt-2 text-[10px] leading-5 text-zinc-500",
                    ),
                ),
                class_name="grid gap-6 p-5 sm:grid-cols-2",
            ),
            class_name="rounded-md border border-white/10 bg-[#191b1e]",
        ),
        rx.el.div(
            rx.el.section(
                section_heading("02", "Monitoring rules", "DETECTION CONTROLS"),
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.p(
                                "Monitoring enabled",
                                class_name="text-sm text-zinc-200",
                            ),
                            rx.el.p(
                                "Collect signals for this tenant and platform.",
                                class_name="mt-2 text-[10px] text-zinc-500",
                            ),
                        ),
                        rx.el.button(
                            rx.icon("power", class_name="h-4 w-4"),
                            rx.cond(
                                ConfigState.draft.monitoring_enabled,
                                "Enabled",
                                "Disabled",
                            ),
                            on_click=ConfigState.toggle_monitoring,
                            disabled=~ConfigState.editable,
                            aria_pressed=ConfigState.draft.monitoring_enabled,
                            class_name="flex items-center gap-2 rounded-md border border-amber-400/30 bg-amber-400/5 px-3 py-2 text-xs text-amber-300 disabled:opacity-50",
                        ),
                        class_name="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5",
                    ),
                    rule_control(
                        "Check interval (seconds)",
                        "interval_seconds",
                        ConfigState.draft.interval_seconds,
                        [15, 30, 60, 120, 300, 600, 1800, 3600],
                        "How often the monitoring service checks pipeline health.",
                    ),
                    rule_control(
                        "Consecutive failure threshold",
                        "failure_threshold",
                        ConfigState.draft.failure_threshold,
                        [1, 2, 3, 5, 10, 20, 50, 100],
                        "Number of consecutive failures before raising an incident.",
                    ),
                    rule_control(
                        "Latency threshold (seconds)",
                        "latency_seconds",
                        ConfigState.draft.latency_seconds,
                        [10, 30, 60, 120, 180, 300, 600, 1800, 3600],
                        "Raise a signal when a run exceeds the configured latency.",
                    ),
                    rx.cond(
                        ~ConfigState.draft.monitoring_enabled,
                        rx.el.p(
                            "Rules are retained while monitoring is disabled.",
                            class_name="text-[10px] text-amber-300",
                        ),
                    ),
                    class_name="flex flex-col gap-5 p-5",
                ),
                class_name="min-w-0 rounded-md border border-white/10 bg-[#191b1e]",
            ),
            rx.el.section(
                section_heading("03", "Remediation policy", "HUMAN OVERSIGHT"),
                rx.el.div(
                    rx.el.label(
                        "Remediation Policy",
                        html_for="config-policy",
                        class_name="mb-2 block text-xs text-zinc-200",
                    ),
                    rx.el.div(
                        rx.el.select(
                            rx.foreach(
                                ConfigState.policies,
                                lambda policy: rx.el.option(
                                    policy.label, value=policy.id
                                ),
                            ),
                            id="config-policy",
                            value=ConfigState.draft.remediation_policy,
                            on_change=ConfigState.set_policy,
                            disabled=~ConfigState.editable,
                            class_name="w-full appearance-none rounded-md border border-white/10 bg-[#202226] px-3 py-3 pr-9 text-xs text-zinc-200 outline-hidden focus:border-amber-400 disabled:opacity-50",
                        ),
                        rx.icon(
                            "chevron-down",
                            class_name="pointer-events-none absolute right-3 top-3 h-4 w-4 text-zinc-500",
                        ),
                        class_name="relative",
                    ),
                    rx.el.p(
                        "Allowed Actions",
                        class_name="mb-3 mt-7 text-xs text-zinc-200",
                    ),
                    rx.el.div(
                        rx.foreach(
                            ["Retry", "Restart", "Rollback"], action_control
                        ),
                        class_name="flex flex-wrap gap-3",
                    ),
                    rx.el.p(
                        "Unavailable actions are disabled according to the service response.",
                        class_name="mt-3 text-[10px] leading-5 text-zinc-500",
                    ),
                    rx.el.div(
                        rx.icon(
                            "shield-check",
                            class_name="h-5 w-5 shrink-0 text-amber-300",
                        ),
                        rx.el.p(
                            "Editing settings does not authorize execution. The service validates access, policy and permitted actions on every save and remediation request.",
                            class_name="text-xs leading-6 text-zinc-400",
                        ),
                        class_name="mt-7 flex gap-3 border-l-2 border-amber-400/50 bg-amber-400/5 p-4",
                    ),
                    rx.cond(
                        ~record.can_edit,
                        rx.el.p(
                            "Read-only access · the service does not permit configuration changes.",
                            class_name="mt-5 text-xs text-amber-300",
                        ),
                    ),
                    class_name="p-5",
                ),
                class_name="min-w-0 rounded-md border border-white/10 bg-[#191b1e]",
            ),
            class_name="grid items-start gap-6 lg:grid-cols-2",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    rx.cond(
                        ConfigState.dirty,
                        "Unsaved local changes",
                        "Matches confirmed configuration",
                    ),
                    class_name="text-xs text-amber-300",
                ),
                rx.el.p(
                    "Switching workspace or reloading discards local edits.",
                    class_name="mt-2 text-[10px] text-zinc-500",
                ),
            ),
            rx.el.div(
                rx.el.button(
                    "Reset to confirmed",
                    on_click=ConfigState.reset_edits,
                    disabled=ConfigState.busy | (~ConfigState.dirty),
                    class_name="rounded-md border border-white/15 px-4 py-3 text-xs text-zinc-300 hover:text-amber-300 disabled:opacity-40",
                ),
                rx.el.button(
                    rx.cond(
                        ConfigState.saving,
                        rx.icon(
                            "loader-circle", class_name="h-4 w-4 animate-spin"
                        ),
                        rx.icon("save", class_name="h-4 w-4"),
                    ),
                    rx.cond(
                        ConfigState.saving, "Saving…", "Save Configuration"
                    ),
                    on_click=ConfigState.save,
                    disabled=(~ConfigState.editable)
                    | (~ConfigState.dirty)
                    | (ConfigState.error_kind != ""),
                    class_name="flex items-center gap-2 rounded-md bg-amber-400 px-4 py-3 text-xs font-semibold text-zinc-950 hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-40",
                ),
                class_name="flex flex-wrap gap-3",
            ),
            class_name="flex flex-wrap items-center justify-between gap-5 rounded-md border border-white/10 bg-[#1b1d20] p-5",
        ),
        rx.el.p(
            f"Revision {record.revision} · Last confirmed {record.updated_at}",
            class_name="break-words font-mono text-[10px] text-zinc-500",
        ),
        rx.cond(
            record.demo,
            rx.el.p(
                "DEVELOPMENT DEMO · synthetic configuration, no live changes",
                class_name="text-[10px] tracking-wide text-amber-300",
            ),
        ),
        class_name="flex flex-col gap-6",
    )


def configuration_content() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "CONFIGURE / MONITOR / GOVERN",
                    class_name="mb-2 text-[9px] tracking-[0.2em] text-amber-400",
                ),
                rx.el.h1(
                    "WORKSPACE CONFIGURATION",
                    class_name="font-['Barlow_Condensed'] text-4xl font-semibold tracking-wide text-zinc-100 sm:text-5xl",
                ),
                rx.el.p(
                    "Set the boundaries. Keep the service in control.",
                    class_name="mt-3 text-xs text-zinc-500",
                ),
            ),
            rx.el.button(
                rx.icon("refresh-cw", class_name="h-4 w-4"),
                "Reload confirmed values",
                on_click=ConfigState.page_load,
                disabled=ConfigState.busy,
                class_name="flex items-center gap-2 rounded-md border border-white/15 bg-[#202226] px-4 py-3 text-xs text-zinc-200 hover:text-amber-300 disabled:opacity-40",
            ),
            class_name="flex flex-wrap items-center justify-between gap-5 py-8",
        ),
        rx.cond(
            ConfigState.error_kind != "",
            rx.el.div(
                rx.icon(
                    "triangle-alert",
                    class_name="h-5 w-5 shrink-0 text-amber-300",
                ),
                rx.el.p(
                    ConfigState.error_message,
                    class_name="text-xs leading-6 text-amber-200",
                ),
                role="alert",
                class_name="mb-6 flex gap-3 rounded-md border border-amber-400/30 bg-amber-400/5 p-5",
            ),
        ),
        rx.cond(
            ConfigState.success != "",
            rx.el.p(
                ConfigState.success,
                role="status",
                class_name="mb-6 rounded-md border border-green-500/20 bg-green-500/10 p-4 text-xs text-green-300",
            ),
        ),
        rx.cond(
            ConfigState.loading,
            rx.el.div(
                rx.icon(
                    "loader-circle",
                    class_name="h-5 w-5 animate-spin text-amber-400",
                ),
                rx.el.p(
                    "Loading authorized configuration…",
                    class_name="text-xs text-zinc-400",
                ),
                rx.el.div(
                    class_name="h-64 w-full animate-pulse rounded-md bg-zinc-800/60"
                ),
                role="status",
                class_name="flex flex-col items-center gap-5",
            ),
            rx.foreach(ConfigState.confirmed, configuration_form),
        ),
        rx.el.section(
            rx.el.h2(
                "Platform configuration",
                class_name="text-sm font-semibold text-zinc-200",
            ),
            rx.cond(
                ConfigState.loading,
                rx.el.p(
                    "Loading platform context…",
                    class_name="mt-3 text-xs text-zinc-400",
                ),
                rx.cond(
                    ConfigState.platform_error != "",
                    rx.el.p(
                        ConfigState.platform_error,
                        role="alert",
                        class_name="mt-3 text-xs text-amber-300",
                    ),
                    rx.cond(
                        ConfigState.platform_configuration.length() > 0,
                        rx.foreach(
                            ConfigState.platform_configuration,
                            lambda config: rx.el.div(
                                rx.el.p(
                                    config.summary,
                                    class_name="mt-3 text-xs text-zinc-300",
                                ),
                                rx.foreach(
                                    ConfigState.platform_entries,
                                    lambda entry: rx.el.div(
                                        rx.el.p(
                                            entry.label,
                                            class_name="text-[10px] uppercase text-zinc-500",
                                        ),
                                        rx.el.pre(
                                            entry.value,
                                            class_name="mt-1 whitespace-pre-wrap break-words text-xs text-zinc-300",
                                        ),
                                        class_name="mt-3",
                                    ),
                                ),
                            ),
                        ),
                        rx.el.p(
                            "No platform configuration reported.",
                            class_name="mt-3 text-xs text-zinc-500",
                        ),
                    ),
                ),
            ),
            class_name="mt-6 rounded-md border border-white/10 bg-[#191b1e] p-5",
        ),
        rx.el.footer(
            "Scoped by tenant. Governed and confirmed by service.",
            class_name="py-6 text-[9px] text-zinc-600",
        ),
        class_name="w-full",
    )
