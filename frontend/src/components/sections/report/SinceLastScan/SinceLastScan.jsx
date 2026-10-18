import { Link } from "react-router-dom";
import Badge from "../../../ui/Badge/Badge";
import { useContent } from "../../../../hooks/useContent";
import { riskTone, severityTone } from "../../../../lib/severity";
import { fill, formatDateTime } from "../../../../lib/text";
import styles from "./SinceLastScan.module.css";

// The order changes are listed and counted in: good news first.
const ORDER = ["fixed", "better", "new", "worse", "not_compared", "same"];
const CHANGE_TONE = {
    fixed: "low",
    better: "low",
    new: "high",
    worse: "high",
    not_compared: "error",
    same: "neutral",
};

const upper = (value) => String(value || "").toUpperCase();

function SeverityBadge({ value }) {
    const { report } = useContent();
    const severity = upper(value) || "ERROR";
    return <Badge tone={severityTone(severity)}>{report.severity[severity] || severity}</Badge>;
}

// "since your last scan": what changed since the person's last finished scan of the same
// address (the backend works it out: scans/compare.py). Shown on every finished report, both
// views. The first scan of an address gets one line saying this is where changes will show.
export default function SinceLastScan({ comparison }) {
    const { report, common } = useContent();
    const copy = report.since;

    if (!comparison) {
        return <p className={`meta-line ${styles.first}`}>{copy.first}</p>;
    }

    const { previous = {}, risk = {}, counts = {}, checks = [] } = comparison;
    const changed = checks
        .filter((item) => item.change !== "same")
        .sort((a, b) => ORDER.indexOf(a.change) - ORDER.indexOf(b.change));
    const before = upper(risk.before);
    const after = upper(risk.after);

    return (
        <section className={styles.deck} aria-labelledby="since-title">
            <div className={styles.head}>
                <h3 id="since-title" className={styles.title}>
                    {copy.title}
                </h3>
                <p className="meta-line">
                    {fill(copy.compared, { date: formatDateTime(previous.scanned_at) })}{" "}
                    {previous.id ? (
                        <Link className={styles.link} to={`/scan/${previous.id}/report`}>
                            {copy.open}
                        </Link>
                    ) : null}
                </p>
            </div>

            <div className={styles.card}>
                <div className={styles.summary}>
                    {before && after ? (
                        <span className={styles.risk}>
                            <span className={styles.label}>{copy.risk}</span>
                            {before === after ? (
                                <span>{copy.unchanged}</span>
                            ) : (
                                <>
                                    <Badge tone={riskTone(before)} bordered={false}>
                                        {common.risk[before] || before}
                                    </Badge>
                                    <span aria-hidden="true">→</span>
                                    <span className="visually-hidden">{copy.to}</span>
                                    <Badge tone={riskTone(after)} bordered={false}>
                                        {common.risk[after] || after}
                                    </Badge>
                                </>
                            )}
                        </span>
                    ) : null}
                    <ul className={styles.counts}>
                        {ORDER.filter((change) => counts[change]).map((change) => (
                            <li key={change}>
                                <Badge tone={CHANGE_TONE[change]} textCase="lower" size="md">
                                    {fill(copy.count[change], { n: counts[change] })}
                                </Badge>
                            </li>
                        ))}
                    </ul>
                </div>

                {changed.length ? (
                    <ul className={styles.list}>
                        {changed.map((item) => (
                            <li key={item.id} className={styles.row}>
                                <span className={styles.name}>{item.check}</span>
                                <span className={styles.move}>
                                    <SeverityBadge value={item.before} />
                                    <span aria-hidden="true">→</span>
                                    <span className="visually-hidden">{copy.to}</span>
                                    <SeverityBadge value={item.after} />
                                </span>
                                <span className={styles.change}>{copy.change[item.change] || item.change}</span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className={styles.nothing}>{copy.nothing}</p>
                )}
                {counts.not_compared ? <p className={styles.note}>{copy.notComparedNote}</p> : null}
            </div>
        </section>
    );
}
