import Badge from "../../../ui/Badge/Badge";
import { useContent } from "../../../../hooks/useContent";
import { severityTone } from "../../../../lib/severity";
import styles from "./Findings.module.css";

// One finding: { check, id, severity, detail: string[], raw, remediation? }
export default function FindingItem({ finding, suggestFix, expanded, onToggle }) {
    const { report } = useContent();
    const severity = String(finding.severity || "ERROR").toUpperCase();
    const details = Array.isArray(finding.detail) ? finding.detail : finding.detail ? [finding.detail] : [];
    const hasRaw = finding.raw && Object.keys(finding.raw).length > 0;

    return (
        <div className={styles.card}>
            <button type="button" className={expanded ? `${styles.header} ${styles.expanded}` : styles.header} onClick={onToggle} aria-expanded={expanded}>
                <span className={styles.titleBlock}>
                    <Badge tone={severityTone(severity)}>{report.severity[severity] || severity}</Badge>
                    <span className={styles.name}>{finding.check}</span>
                </span>
                <span className={styles.aside}>
                    <span className={styles.id}>{finding.id}</span>
                    <span className={styles.caret} aria-hidden="true">
                        {expanded ? "▲" : "▼"}
                    </span>
                </span>
            </button>

            {expanded ? (
                <div className={styles.body}>
                    {details.length ? (
                        <ul className={styles.detailList}>
                            {details.map((line, index) => (
                                <li key={index} className={styles.detail}>
                                    {line}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className={styles.detail}>{report.findings.noDetail}</p>
                    )}

                    {hasRaw ? (
                        <div className={styles.code}>
                            <span className={styles.codeHeader}>{report.findings.raw}</span>
                            <pre className={styles.codeBlock}>
                                <code>{JSON.stringify(finding.raw, null, 2)}</code>
                            </pre>
                        </div>
                    ) : null}

                    {suggestFix && finding.remediation ? (
                        <div className={styles.remediation}>
                            <strong>{report.findings.remediation}</strong> {finding.remediation}
                        </div>
                    ) : null}
                </div>
            ) : null}
        </div>
    );
}
