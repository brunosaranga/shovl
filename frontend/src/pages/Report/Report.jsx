import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import PageBody from "../../components/layout/PageBody/PageBody";
import PageTitle from "../../components/ui/PageTitle/PageTitle";
import Alert from "../../components/ui/Alert/Alert";
import Button from "../../components/ui/Button/Button";
import ReportMeta from "../../components/sections/report/ReportMeta/ReportMeta";
import CoverageNote from "../../components/sections/report/CoverageNote/CoverageNote";
import SeverityMatrix from "../../components/sections/report/SeverityMatrix/SeverityMatrix";
import FixList from "../../components/sections/report/FixList/FixList";
import Findings from "../../components/sections/report/Findings/Findings";
import ScanState from "../../components/sections/report/ScanState/ScanState";
import { useContent } from "../../hooks/useContent";
import { useScanDetail } from "../../hooks/useScans";
import { useScanOutcomeSound, useSoundCue } from "../../hooks/useSounds";
import styles from "./Report.module.css";

// The scan options only add to the report, never hide each other:
//   always          → score, coverage, severity counts
//   generate report → the per-check breakdown (findings) is shown straight away
//   suggest fix     → a fix for every problem: inside each finding, or, on the summary view,
//                     in its own "how to fix" section
//   verbose         → the raw responses inside each finding
// Every finding is saved whichever options were on, so "show full report" opens the breakdown
// on a summary view in place, without spending a scan. ("generate report" is meant to become
// a downloadable PDF once PDFs are switched on; until then it only picks the starting view.)
export default function Report() {
    const { report } = useContent();
    const { scanId } = useParams();
    const navigate = useNavigate();
    const { scan, loading, error } = useScanDetail(scanId);
    // The view picked on this page ("full" | "summary"), remembered per scan.
    const [picked, setPicked] = useState({ scanId: null, view: null });

    // Error cue when the report can't load; the outcome cue when a running scan finishes here.
    useSoundCue("error", error && !scan ? error : null);
    useScanOutcomeSound(scan?.status);

    const results = scan?.results || null;
    const meta = results?.meta;
    const summaryFirst = meta?.generate_report === false;
    const view = picked.scanId === scanId && picked.view ? picked.view : summaryFirst ? "summary" : "full";
    const pick = (next) => setPicked({ scanId, view: next });

    const reRun = () =>
        navigate("/scan/running", {
            state: {
                url: scan.target_url,
                verbose: scan.verbose,
                suggest_fix: scan.suggest_fix,
                generate_report: meta?.generate_report ?? true,
            },
        });

    return (
        <>
            <PageMeta title={report.meta} />
            <NavCenter>
                <PageTitle>{report.pageTitle}</PageTitle>
            </NavCenter>

            <PageBody width="wide" gap="md" mono>
                {loading && !scan ? <p className="meta-line">{report.loading}</p> : null}

                {error && !scan ? (
                    <Alert title={error.response?.status === 404 ? report.notFound : report.loadFailed} role="alert" />
                ) : null}

                {scan && scan.status !== "complete" ? <ScanState scan={scan} onReRun={reRun} /> : null}

                {scan?.status === "complete" && results ? (
                    <>
                        <ReportMeta meta={meta} targetUrl={scan.target_url} onReRun={reRun} />
                        <CoverageNote meta={meta} findings={results.findings} summary={results.summary} />
                        <SeverityMatrix summary={results.summary} />

                        {view === "full" ? (
                            <>
                                {summaryFirst ? (
                                    <div className={styles.viewBar}>
                                        <Button variant="small" onClick={() => pick("summary")}>
                                            {report.view.hide}
                                        </Button>
                                    </div>
                                ) : null}
                                <Findings findings={results.findings || []} suggestFix={meta?.suggest_fix} />
                            </>
                        ) : (
                            <>
                                {meta?.suggest_fix ? <FixList findings={results.findings || []} /> : null}
                                <div className={styles.summaryNote}>
                                    <p className="meta-line">{meta?.verbose ? report.view.noteVerbose : report.view.note}</p>
                                    <Button variant="small" onClick={() => pick("full")}>
                                        {report.view.show}
                                    </Button>
                                </div>
                            </>
                        )}
                    </>
                ) : null}
            </PageBody>
        </>
    );
}
