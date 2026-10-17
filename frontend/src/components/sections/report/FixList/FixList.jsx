import Badge from "../../../ui/Badge/Badge";
import { useContent } from "../../../../hooks/useContent";
import { SEVERITY_ORDER, severityTone } from "../../../../lib/severity";
import styles from "./FixList.module.css";

const upper = (value) => String(value || "").toUpperCase();
const rank = (finding) => {
    const index = SEVERITY_ORDER.indexOf(upper(finding.severity));
    return index === -1 ? SEVERITY_ORDER.length : index;
};

// "how to fix": one row per problem, worst first, with the fix and nothing else.
// Shown on the summary view of a scan that had "suggest fix" on. The backend attaches a
// remediation to every finding that isn't a PASS or an ERROR (scanner/report.py), so the
// findings that carry one are exactly the problems.
export default function FixList({ findings = [] }) {
    const { report } = useContent();
    const problems = findings
        .map((finding, index) => ({ finding, index }))
        .filter(({ finding }) => finding.remediation)
        .sort((a, b) => rank(a.finding) - rank(b.finding) || a.index - b.index);

    return (
        <section className={styles.deck} aria-labelledby="fix-list-title">
            <div className={styles.head}>
                <h3 id="fix-list-title" className={styles.title}>
                    {report.fixes.title}
                </h3>
                <p className="meta-line">{problems.length ? report.fixes.lead : report.fixes.none}</p>
            </div>

            {problems.length ? (
                <ul className={styles.list}>
                    {problems.map(({ finding, index }) => {
                        const severity = upper(finding.severity);
                        return (
                            <li key={`${finding.id || "finding"}-${index}`} className={styles.item}>
                                <div className={styles.header}>
                                    <span className={styles.titleBlock}>
                                        <Badge tone={severityTone(severity)}>{report.severity[severity] || severity}</Badge>
                                        <span className={styles.name}>{finding.check}</span>
                                    </span>
                                    <span className={styles.id}>{finding.id}</span>
                                </div>
                                <p className={styles.fix}>{finding.remediation}</p>
                            </li>
                        );
                    })}
                </ul>
            ) : null}
        </section>
    );
}
