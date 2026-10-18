import Card from "../../../ui/Card/Card";
import Badge from "../../../ui/Badge/Badge";
import Button from "../../../ui/Button/Button";
import { useContent } from "../../../../hooks/useContent";
import { riskTone } from "../../../../lib/severity";
import { formatDateTime } from "../../../../lib/text";
import styles from "./ReportMeta.module.css";

// Top strip: target, when it ran, the overall risk score, and the actions:
// "download pdf" (free, any finished scan) and "re-run scan" (uses up a scan).
export default function ReportMeta({ meta, targetUrl, onReRun, onDownload, downloading = false }) {
    const { report, common } = useContent();
    const risk = String(meta?.risk_score || "").toUpperCase();

    return (
        <Card border={3} shadow={6} className={styles.card}>
            <div className={styles.details}>
                <div className={styles.line}>
                    <span className={styles.label}>{report.labels.target}</span>
                    <span className={styles.value}>{meta?.target || targetUrl || "—"}</span>
                </div>
                <div className={styles.line}>
                    <span className={styles.label}>{report.labels.runtime}</span>
                    <span>{formatDateTime(meta?.scanned_at)}</span>
                </div>
                <div className={styles.line}>
                    <span className={styles.label}>{report.labels.risk}</span>
                    <Badge tone={riskTone(risk)} bordered={false}>
                        {common.risk[risk] || common.risk.none}
                    </Badge>
                </div>
            </div>
            <div className={styles.actions}>
                {onDownload ? (
                    <Button onClick={onDownload} disabled={downloading} aria-busy={downloading}>
                        {downloading ? report.pdf.preparing : report.pdf.download}
                    </Button>
                ) : null}
                <Button onClick={onReRun}>{report.rerun}</Button>
            </div>
        </Card>
    );
}
