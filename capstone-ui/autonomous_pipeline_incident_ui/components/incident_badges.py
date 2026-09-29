import reflex as rx


def status_badge(status: str) -> rx.Component:
    return rx.el.span(
        rx.el.span(class_name="h-1 w-1 rounded-full bg-current"),
        rx.el.span(
            status.to(str).lower().split("_").join(" "), class_name="capitalize"
        ),
        class_name=rx.match(
            status,
            (
                "DETECTED",
                "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-sky-400/20 bg-sky-400/10 px-2 py-1 text-[10px] text-sky-300",
            ),
            (
                "INVESTIGATING",
                "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-blue-400/20 bg-blue-400/10 px-2 py-1 text-[10px] text-blue-300",
            ),
            (
                "DIAGNOSED",
                "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-indigo-400/20 bg-indigo-400/10 px-2 py-1 text-[10px] text-indigo-300",
            ),
            (
                "REMEDIATION_PROPOSED",
                "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-violet-400/20 bg-violet-400/10 px-2 py-1 text-[10px] text-violet-300",
            ),
            (
                "AWAITING_APPROVAL",
                "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-[10px] text-amber-300",
            ),
            (
                "REMEDIATING",
                "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-orange-400/20 bg-orange-400/10 px-2 py-1 text-[10px] text-orange-300",
            ),
            (
                "VALIDATING",
                "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-teal-400/20 bg-teal-400/10 px-2 py-1 text-[10px] text-teal-300",
            ),
            (
                "RESOLVED",
                "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[10px] text-emerald-300",
            ),
            (
                "REJECTED",
                "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-rose-400/20 bg-rose-400/10 px-2 py-1 text-[10px] text-rose-300",
            ),
            (
                "ESCALATED",
                "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-red-400/40 bg-red-400/15 px-2 py-1 text-[10px] font-semibold text-red-300",
            ),
            "inline-flex w-fit items-center gap-1.5 whitespace-nowrap rounded-sm border border-zinc-500/20 bg-zinc-500/10 px-2 py-1 text-[10px] text-zinc-300",
        ),
    )


def severity_badge(severity: str) -> rx.Component:
    return rx.el.span(
        rx.icon("signal", class_name="h-3 w-3"),
        severity,
        class_name=rx.match(
            severity,
            (
                "CRITICAL",
                "inline-flex w-fit items-center gap-1.5 text-[10px] font-semibold text-red-300",
            ),
            (
                "HIGH",
                "inline-flex w-fit items-center gap-1.5 text-[10px] text-amber-300",
            ),
            (
                "MEDIUM",
                "inline-flex w-fit items-center gap-1.5 text-[10px] text-yellow-200",
            ),
            "inline-flex w-fit items-center gap-1.5 text-[10px] text-zinc-400",
        ),
    )
