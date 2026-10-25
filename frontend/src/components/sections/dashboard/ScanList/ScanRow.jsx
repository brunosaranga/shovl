import Badge from "../../../ui/Badge/Badge";
import Button from "../../../ui/Button/Button";
import { useContent } from "../../../../hooks/useContent";
import { isInProgress, riskTone, statusTone } from "../../../../lib/severity";
import { fill, formatDate } from "../../../../lib/text";
import styles from "./ScanList.module.css";

// One scan in the list. Opening it shows a summary that depends on how the scan ended.
// Scheduled scans (shovll watch) carry a "watch" tag next to their status.
export default function ScanRow({ scan, expanded, onToggle }) {
    const { dashboard, common } = useContent();
    const risk = String(scan.risk_score || "").toUpperCase();
    const report = `/scan/${scan.id}/report`;
    const meta = scan.results?.meta;
    const summary = scan.results?.summary || {};

    return (
        <div className={styles.card}>
            <div className={expanded ? `${styles.header} ${styles.open}` : styles.header}>
                <div className={styles.left}>
                    <span className={styles.badges}>
                        <Badge tone={statusTone(scan.status)} size="md" textCase="lower">
                            {common.status[scan.status] || scan.status}
                        </Badge>
                        {scan.trigger === "watch" ? (
                            <span className={styles.watchTag} title={dashboard.row.watchTitle}>
                                <Badge tone="accent" size="md" textCase="lower">
                                    {dashboard.row.watch}
                                </Badge>
                            </span>
                        ) : null}
                    </span>
                    <span className={styles.target}>{scan.target_url}</span>
                </div>

                <div className={styles.right}>
                    <span className={styles.date}>{formatDate(scan.created_at)}</span>
                    {scan.status === "complete" && risk ? (
                        <Badge tone={riskTone(risk)} size="sm">
                            {`!!! ${common.risk[risk] || risk}`}
                        </Badge>
                    ) : null}
                    <button
                        type="button"
                        onClick={onToggle}
                        className={expanded ? `${styles.toggle} ${styles.toggleOpen}` : styles.toggle}
                        aria-expanded={expanded}
                        aria-label={dashboard.row.toggle}
                    >
                        ➔
                    </button>
                </div>
            </div>

            {expanded ? (
                <div className={styles.panel}>
                    {scan.status === "complete" ? (
                        <>
                            <span className={styles.panelLabel}>{dashboard.row.summary}</span>
                            <div>{fill(dashboard.row.counts, { HIGH: 0, MEDIUM: 0, LOW: 0, PASS: 0, ...summary })}</div>
                            {meta?.partial ? (
                                <div className={styles.muted}>
                                    {fill(dashboard.row.coverage, { run: meta.checks_run, total: meta.total_checks })}
                                </div>
                            ) : null}
                            <Button to={report} variant="dark" className={styles.panelAction}>
                                {dashboard.row.view}
                            </Button>
                        </>
                    ) : null}

                    {isInProgress(scan.status) ? (
                        <>
                            <div>{scan.status === "paused" ? dashboard.row.paused : dashboard.row.running}</div>
                            <Button to={report} variant="dark" className={styles.panelAction}>
                                {dashboard.row.open}
                            </Button>
                        </>
                    ) : null}

                    {scan.status === "failed" ? (
                        <>
                            <div>{scan.results?.error?.message}</div>
                            <div className={styles.muted}>{common.didNotCount}</div>
                        </>
                    ) : null}

                    {scan.status === "interrupted" ? (
                        <>
                            <div>{dashboard.row.interrupted}</div>
                            <div className={styles.muted}>{common.didNotCount}</div>
                        </>
                    ) : null}

                    {scan.status === "stopped" ? (
                        <>
                            <div>{scan.results?.error?.message || dashboard.row.stopped}</div>
                            <div className={styles.muted}>{common.didNotCount}</div>
                        </>
                    ) : null}
                </div>
            ) : null}
        </div>
    );
}
