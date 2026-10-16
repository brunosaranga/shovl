import { useCallback, useEffect, useRef, useState } from "react";
import { openScanStream, scansApi } from "../lib/api";
import { describeResponse } from "../lib/apiErrors";
import { readEvents, readJsonBody } from "../lib/sse";
import { fill } from "../lib/text";
import { useContent } from "./useContent";

const MAX_LOG_LINES = 14;

// Runs one scan over GET /api/scans/stream/ and reports what happens.
//
//   phase:    "connecting" | "running" | "complete" | "failed" | "stopped" | "refused" | "error"
//   control:  "running" | "pausing" | "paused" | "resuming"   (the pause button, while phase is "running")
//   problem:  { kind: "refused" | "failed" | "stopped" | "error", code, message, retryAfter, scanId } or null
//
// Stream events from the backend, in order:
//   started { scan_id }: the id that pause, resume and stop need
//   running (check: reachability), then running + result per check, then complete
//   result.severity can be ERROR: the check could not run (e.g. mass assignment on a real domain)
//   a scan that cannot produce a result sends error, then failed { scan_id, reason, message }
//   between two checks: paused, then resumed, or stopped { scan_id, reason, message }
// A refusal (allowance, guest on a real domain, unverified domain) is a non-200 with a JSON body.
//
// pause(), resume() and stop() call POST /api/scans/<id>/pause|resume|stop/. The backend pauses
// after the check in flight, so control reads "pausing" until the stream says "paused".
// stop() records the stop before it closes the stream, so the dashboard shows it straight away.
// restart() runs the same scan again (the "try again" button).
export function useScanStream({ options, enabled = true }) {
    const { scan, report, errors } = useContent();
    const [phase, setPhase] = useState("connecting");
    const [control, setControl] = useState("running");
    const [progress, setProgress] = useState(0);
    const [logs, setLogs] = useState(scan.terminal.boot);
    const [scanId, setScanId] = useState(null);
    const [problem, setProblem] = useState(null);

    const [runId, setRunId] = useState(0);
    const controllerRef = useRef(null);
    const scanIdRef = useRef(null);
    const controlRef = useRef("running");
    const stoppingRef = useRef(false); // the stop button was pressed: the page is on its way out

    const url = options?.url;
    const verbose = Boolean(options?.verbose);
    const suggestFix = Boolean(options?.suggest_fix);
    const generateReport = options?.generate_report !== false;

    const updateControl = useCallback((value) => {
        controlRef.current = value;
        setControl(value);
    }, []);

    useEffect(() => {
        if (!enabled || !url) return undefined;

        const controller = new AbortController();
        controllerRef.current = controller;
        scanIdRef.current = null;
        stoppingRef.current = false;
        let finished = false;

        const now = () => new Date().toLocaleTimeString();

        const log = (line) => {
            setLogs((previous) => [...previous, line].slice(-MAX_LOG_LINES));
        };

        const track = (event) => {
            if (event.total) setProgress(Math.round((event.progress / event.total) * 100));
        };

        const handle = (event) => {
            if (event.status === "started") {
                scanIdRef.current = event.scan_id;
                setScanId(event.scan_id);
            } else if (event.status === "running") {
                log(fill(scan.terminal.running, { time: now(), check: event.check }));
                track(event);
            } else if (event.status === "result") {
                const severity = String(event.severity || "").toUpperCase();
                const detail = Array.isArray(event.detail) ? event.detail.join("; ") : event.detail || "";
                log(
                    fill(scan.terminal.result, {
                        check: event.check,
                        severity: report.severity[severity] || severity.toLowerCase(),
                        detail,
                    })
                );
                track(event);
            } else if (event.status === "paused") {
                updateControl("paused");
                log(fill(scan.terminal.paused, { time: now() }));
            } else if (event.status === "resumed") {
                updateControl("running");
                log(fill(scan.terminal.resumed, { time: now() }));
            } else if (event.status === "error") {
                log(fill(scan.terminal.error, { check: event.check, message: event.message }));
            } else if (event.status === "failed") {
                finished = true;
                setPhase("failed");
                setScanId(event.scan_id ?? null);
                setProblem({
                    kind: "failed",
                    code: event.reason,
                    message: event.message || report.state.failed.text,
                    scanId: event.scan_id ?? null,
                });
            } else if (event.status === "stopped") {
                finished = true;
                // After the stop button the page is already leaving: nothing to show.
                if (stoppingRef.current) return;
                // Otherwise it was stopped elsewhere, or paused for too long.
                setPhase("stopped");
                setProblem({
                    kind: "stopped",
                    code: event.reason,
                    message: event.message || report.state.stopped.text,
                    scanId: event.scan_id ?? null,
                });
            } else if (event.status === "complete") {
                finished = true;
                setProgress(100);
                setScanId(event.scan_id);
                setPhase("complete");
            }
        };

        const run = async () => {
            try {
                const response = await openScanStream(
                    { url, verbose, suggest_fix: suggestFix, generate_report: generateReport },
                    { signal: controller.signal }
                );

                if (!response.ok) {
                    const body = await readJsonBody(response);
                    const described = describeResponse(response.status, body, errors);
                    finished = true;
                    setPhase("refused");
                    setProblem({ kind: "refused", ...described });
                    return;
                }

                setPhase("running");
                for await (const event of readEvents(response)) {
                    handle(event);
                }

                if (!finished) {
                    setPhase("error");
                    setProblem({ kind: "error", code: "stream_ended", message: scan.problems.streamEnded });
                }
            } catch (error) {
                if (error.name === "AbortError") return;
                setPhase("error");
                setProblem({ kind: "error", code: "network", message: errors.network });
            }
        };

        // Started on the next tick: React's development double-mount unmounts straight away,
        // which cancels this timer, so dev never opens (and interrupts) a second scan.
        const timer = setTimeout(run, 0);
        return () => {
            clearTimeout(timer);
            controller.abort();
        };
    }, [enabled, runId, url, verbose, suggestFix, generateReport, scan, report, errors, updateControl]);

    const pause = useCallback(async () => {
        const id = scanIdRef.current;
        if (!id || controlRef.current !== "running") return;
        updateControl("pausing");
        try {
            const { data } = await scansApi.pause(id);
            if (data?.status !== "paused" && controlRef.current === "pausing") updateControl("running");
        } catch {
            // 409: the scan ended first (the stream says how). Otherwise the request failed: nothing paused.
            if (controlRef.current === "pausing") updateControl("running");
        }
    }, [updateControl]);

    const resume = useCallback(async () => {
        const id = scanIdRef.current;
        const before = controlRef.current;
        if (!id || (before !== "paused" && before !== "pausing")) return;
        updateControl("resuming");
        try {
            await scansApi.resume(id);
            // Resumed before the scan reached its next check: it never held, so no "resumed" event comes.
            if (before === "pausing" && controlRef.current === "resuming") updateControl("running");
        } catch {
            if (controlRef.current === "resuming") updateControl(before);
        }
    }, [updateControl]);

    const stop = useCallback(async () => {
        stoppingRef.current = true;
        const id = scanIdRef.current;
        if (id) {
            try {
                await scansApi.stop(id);
            } catch {
                // Not recorded (already finished, or the request failed): closing the stream below
                // still ends the scan, which is then marked interrupted.
            }
        }
        controllerRef.current?.abort();
    }, []);

    const restart = () => {
        scanIdRef.current = null;
        stoppingRef.current = false;
        updateControl("running");
        setPhase("connecting");
        setProgress(0);
        setLogs(scan.terminal.boot);
        setScanId(null);
        setProblem(null);
        setRunId((id) => id + 1);
    };

    return {
        phase,
        isActive: Boolean(enabled && url) && (phase === "connecting" || phase === "running"),
        control,
        progress,
        logs,
        scanId,
        problem,
        pause,
        resume,
        stop,
        restart,
    };
}
