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
import Findings from "../../components/sections/report/Findings/Findings";
import ScanState from "../../components/sections/report/ScanState/ScanState";
import { useContent } from "../../hooks/useContent";
import { useScanDetail } from "../../hooks/useScans";
import { useScanOutcomeSound, useSoundCue } from "../../hooks/useSounds";
import styles from "./Report.module.css";

export default function Report() {
    const { report } = useContent();
    const { scanId } = useParams();
    const navigate = useNavigate();
    const { scan, loading, error } = useScanDetail(scanId);

    // Error cue when the report can't load; the outcome cue when a running scan finishes here.
    useSoundCue("error", error && !scan ? error : null);
    useScanOutcomeSound(scan?.status);

    const results = scan?.results || null;
    const meta = results?.meta;

    const reRun = (fullReport = false) =>
        navigate("/scan/running", {
            state: {
                url: scan.target_url,
                verbose: scan.verbose,
                suggest_fix: scan.suggest_fix,
                generate_report: fullReport ? true : (meta?.generate_report ?? true),
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

                {scan && scan.status !== "complete" ? <ScanState scan={scan} onReRun={() => reRun()} /> : null}

                {scan?.status === "complete" && results ? (
                    <>
                        <ReportMeta meta={meta} targetUrl={scan.target_url} onReRun={() => reRun()} />
                        <CoverageNote meta={meta} findings={results.findings} summary={results.summary} />
                        <SeverityMatrix summary={results.summary} />

                        {meta?.generate_report !== false ? (
                            <Findings findings={results.findings || []} suggestFix={meta?.suggest_fix} />
                        ) : (
                            <div className={styles.summaryNote}>
                                <p className="meta-line">{report.summaryOnly}</p>
                                <Button variant="small" onClick={() => reRun(true)}>
                                    {report.rerunFull}
                                </Button>
                            </div>
                        )}
                    </>
                ) : null}
            </PageBody>
        </>
    );
}
