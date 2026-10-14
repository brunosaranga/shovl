import Card from "../../../ui/Card/Card";
import Badge from "../../../ui/Badge/Badge";
import Button from "../../../ui/Button/Button";
import { useContent } from "../../../../hooks/useContent";
import { riskTone } from "../../../../lib/severity";
import { fill } from "../../../../lib/text";
import styles from "./ScanStats.module.css";

const THREATS = [
    { risk: "CRITICAL", short: "CRIT" },
    { risk: "HIGH", short: "HIGH" },
    { risk: "MEDIUM", short: "MED" },
];

// Active scans · threat alerts (completed scans by risk) · scans left · new scan.
export default function ScanStats({ scans, allowance, isGuest }) {
    const { dashboard } = useContent();

    const active = scans.filter((scan) => scan.status === "running" || scan.status === "pending").length;
    const threats = THREATS.map((threat) => ({
        ...threat,
        count: scans.filter((scan) => scan.status === "complete" && String(scan.risk_score).toUpperCase() === threat.risk).length,
    })).filter((threat) => threat.count > 0);

    const remaining = allowance
        ? fill(isGuest ? dashboard.stats.remainingGuest : dashboard.stats.remainingDay, allowance)
        : dashboard.stats.unlimited;

    return (
        <Card border={3} shadow={6} className={styles.card}>
            <div className={styles.stats}>
                <div>
                    <span className={styles.label}>{dashboard.stats.active}</span>
                    <span className={styles.number}>{active}</span>
                </div>

                <div className={styles.divider} />

                <div>
                    <span className={styles.label}>{dashboard.stats.threats}</span>
                    <div className={styles.chips}>
                        {threats.length ? (
                            threats.map((threat) => (
                                <Badge key={threat.risk} tone={riskTone(threat.risk)} size="xs" bordered={false}>
                                    {fill(dashboard.stats.threatChip, { label: threat.short, count: threat.count })}
                                </Badge>
                            ))
                        ) : (
                            <span className={styles.none}>{dashboard.stats.noThreats}</span>
                        )}
                    </div>
                </div>

                <div className={styles.divider} />

                <div>
                    <span className={styles.label}>{dashboard.stats.remaining}</span>
                    <span className={styles.remaining}>{remaining}</span>
                </div>
            </div>

            <Button to="/">{dashboard.newScan}</Button>
        </Card>
    );
}
