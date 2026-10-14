import { useState } from "react";
import Button from "../../../ui/Button/Button";
import FindingItem from "./FindingItem";
import { useContent } from "../../../../hooks/useContent";
import styles from "./Findings.module.css";

// Findings have no unique id (the OWASP id can repeat), so key on id + position.
const keyOf = (finding, index) => `${finding?.id || "finding"}-${index}`;

// The accordion of findings. Everything that isn't a PASS starts open.
export default function Findings({ findings = [], suggestFix }) {
    const { report } = useContent();
    const keys = findings.map(keyOf);
    const [open, setOpen] = useState(
        () =>
            new Set(
                findings
                    .map((finding, index) => [finding, keyOf(finding, index)])
                    .filter(([finding]) => String(finding.severity).toUpperCase() !== "PASS")
                    .map(([, key]) => key)
            )
    );

    const toggle = (key) =>
        setOpen((previous) => {
            const next = new Set(previous);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
        });

    if (!findings.length) {
        return (
            <div className={styles.deck}>
                <h3 className={styles.title}>{report.findings.title}</h3>
                <p className="meta-line">{report.findings.empty}</p>
            </div>
        );
    }

    const allOpen = keys.every((key) => open.has(key));

    return (
        <div className={styles.deck}>
            <div className={styles.head}>
                <h3 className={styles.title}>{report.findings.title}</h3>
                <div className={styles.controls}>
                    <Button variant="small" onClick={() => setOpen(new Set(keys))} disabled={allOpen}>
                        {report.findings.expandAll}
                    </Button>
                    <Button variant="small" onClick={() => setOpen(new Set())} disabled={open.size === 0}>
                        {report.findings.collapseAll}
                    </Button>
                </div>
            </div>

            {findings.map((finding, index) => {
                const key = keyOf(finding, index);
                return (
                    <FindingItem
                        key={key}
                        finding={finding}
                        suggestFix={suggestFix}
                        expanded={open.has(key)}
                        onToggle={() => toggle(key)}
                    />
                );
            })}
        </div>
    );
}
