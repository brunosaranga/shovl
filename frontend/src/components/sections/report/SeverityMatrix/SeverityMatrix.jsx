import { useContent } from "../../../../hooks/useContent";
import { SEVERITY_ORDER, severityTone } from "../../../../lib/severity";
import styles from "./SeverityMatrix.module.css";

// How many findings landed in each severity. CRITICAL only exists as an overall
// risk score (see ReportMeta), never per finding.
export default function SeverityMatrix({ summary = {} }) {
    const { report } = useContent();
    return (
        <div className={styles.grid}>
            {SEVERITY_ORDER.map((key) => (
                <div key={key} className={styles.box}>
                    <div className={`${styles.header} ${styles[severityTone(key)]}`}>{report.matrix[key]}</div>
                    <div className={styles.count}>{summary[key] ?? 0}</div>
                </div>
            ))}
        </div>
    );
}
