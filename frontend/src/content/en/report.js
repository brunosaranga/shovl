export const report = {
    meta: "report | shovl",
    pageTitle: "report",

    loading: "loading report...",
    notFound: "Report not found.",
    loadFailed: "Failed to load report.",

    labels: {
        target: "target: ",
        runtime: "runtime: ",
        risk: "risk score: ",
    },

    rerun: "re-run scan",

    // "download pdf": built from the saved scan, so any finished scan has one, for free.
    pdf: {
        download: "download pdf",
        preparing: "preparing pdf...",
        errors: {
            disabled: "PDF downloads are switched off for now. the report on this page has everything.",
            tooMany: "that's a lot of downloads in a short time. try again in a little while.",
            notComplete: "only a finished scan has a report to download.",
            failed: "couldn't make the PDF. try again in a moment.",
        },
    },

    // What changed since the person's last finished scan of the same address (scans/compare.py).
    since: {
        title: "since your last scan",
        compared: "compared with your scan of {date}.",
        open: "open that report",
        risk: "risk score:",
        unchanged: "unchanged",
        to: "to",
        nothing: "nothing changed: every check has the same result as last time.",
        first: "first scan of this address. fix something and scan it again: this is where you'll see what changed.",
        notComparedNote: "can't compare: the check ran in only one of the two scans.",
        change: {
            fixed: "fixed",
            better: "better",
            new: "new problem",
            worse: "worse",
            not_compared: "can't compare",
            same: "unchanged",
        },
        count: {
            fixed: "{n} fixed",
            better: "{n} better",
            new: "{n} new",
            worse: "{n} worse",
            not_compared: "{n} can't compare",
            same: "{n} unchanged",
        },
    },

    // "was this report useful?" at the bottom of a finished report. All of it is optional.
    feedback: {
        title: "was this report useful?",
        lead: "optional. one click helps decide what shovl does next.",
        yes: "yes",
        no: "not really",
        skip: "skip",
        followUp: "thanks. two more, both optional:",
        done: "done",
        sending: "sending...",
        comment: {
            label: "what would make it more useful?",
            placeholder: "anything missing, confusing or wrong",
            send: "send",
            sent: "sent.",
            count: "{n}/{max}",
        },
        pay: {
            question: "would you pay for shovl to scan your API every week and email you when something changes?",
            yes: "yes",
            maybe: "maybe",
            no: "no",
        },
        thanks: "thanks for the feedback.",
        change: "change your answer",
        errors: {
            failed: "couldn't save that. try again.",
            tooMany: "too many answers in a short time. try again later.",
        },
    },

    // A scan run with "generate report" off opens on the summary view. The breakdown was saved
    // anyway, so opening it is free: no new scan.
    view: {
        note: "summary view: \"generate report\" was off for this scan, so the per-check breakdown is hidden. it was saved with the scan, so opening it doesn't use up a scan.",
        noteVerbose:
            "summary view: \"generate report\" was off for this scan, so the per-check breakdown and the raw responses are hidden. both were saved with the scan, so opening them doesn't use up a scan.",
        show: "show full report",
        hide: "back to summary",
    },

    // The summary view's fixes, when "suggest fix" was on.
    fixes: {
        title: "how to fix",
        lead: "one fix per problem, worst first. the full report has the evidence behind each one.",
        none: "nothing to fix: every check that ran passed.",
    },

    coverage: {
        partial: "based on {run} of {total} checks.",
        incomplete: "0 of {total} checks completed — shovl couldn't assess this target. re-run the scan.",
        notRunTitle: "checks that could not run:",
    },

    matrix: {
        HIGH: "High",
        MEDIUM: "Medium",
        LOW: "Low",
        PASS: "Passed",
        ERROR: "Errors",
    },

    // Badge on each finding. ERROR means the check could not run, not that something was found.
    severity: {
        HIGH: "high",
        MEDIUM: "medium",
        LOW: "low",
        PASS: "pass",
        ERROR: "could not run",
    },

    findings: {
        title: "vulnerability findings",
        expandAll: "expand all",
        collapseAll: "collapse all",
        empty: "No findings returned for this scan.",
        noDetail: "No additional detail.",
        raw: "Raw response data (verbose)",
        remediation: "remediation suggestion:",
    },

    // Scans that are not complete.
    state: {
        running: {
            title: "still digging.",
            text: "this scan is still running. this page updates when it finishes.",
        },
        paused: {
            title: "scan paused.",
            text: "this scan is paused on its scan page. this page updates when it resumes or ends.",
        },
        failed: {
            title: "scan failed.",
            text: "the scan could not produce a result.",
        },
        interrupted: {
            title: "scan interrupted.",
            text: "the scan stopped before it finished, usually because the page was closed.",
        },
        stopped: {
            title: "scan stopped.",
            text: "this scan was stopped before it finished.",
        },
    },
};
