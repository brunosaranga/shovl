import { useNavigate } from "react-router-dom";
import Badge from "../../ui/Badge/Badge";
import { useNotifications } from "../../../context/NotificationsContext";
import { useContent } from "../../../hooks/useContent";
import { riskTone, severityTone } from "../../../lib/severity";
import { formatAgo } from "../../../lib/text";
import BellRow from "./BellRow";
import styles from "./BellModal.module.css";

// A stored item: "shovll watch is on", "now watching ...", or an alert when a watched API got
// worse. Opening it marks it read; unread ones carry a "new" chip. An alert shows the risk
// before → after and each check that changed, with a button to its report.
export default function NewsItem({ item }) {
    const { notifications: copy, common } = useContent();
    const { closeBell, markRead } = useNotifications();
    const navigate = useNavigate();

    const go = (to) => {
        closeBell();
        navigate(to);
    };

    const info = (
        <>
            {!item.read ? <span className={styles.newChip}>{copy.unread}</span> : null}
            {formatAgo(item.created_at)}
        </>
    );

    const risk = item.data?.risk;
    const changes = item.data?.changes || [];

    return (
        <BellRow title={item.title} info={info} onOpen={() => !item.read && markRead(item.id)}>
            {/* An alert's details say what its summary says, item by item. */}
            {item.kind === "alert" && risk ? null : <p className={styles.summary}>{item.summary}</p>}

            {item.kind === "alert" && risk ? (
                <div className={styles.alert}>
                    <p className={styles.alertLine}>
                        <span className={styles.label}>{copy.alert.risk}</span>
                        <Badge tone={riskTone(risk.before)}>{common.risk[risk.before] || risk.before}</Badge>
                        <span aria-hidden="true">→</span>
                        <Badge tone={riskTone(risk.after)}>{common.risk[risk.after] || risk.after}</Badge>
                    </p>
                    {changes.length ? (
                        <>
                            <p className={styles.label}>{copy.alert.changes}</p>
                            <ul className={styles.changes}>
                                {changes.map((change) => (
                                    <li key={change.id} className={styles.change}>
                                        <span className={styles.changeName}>{change.check}</span>
                                        <span className={styles.changeBadges}>
                                            <Badge tone={severityTone(change.before)} size="xs">
                                                {change.before}
                                            </Badge>
                                            <span aria-hidden="true">→</span>
                                            <Badge tone={severityTone(change.after)} size="xs">
                                                {change.after}
                                            </Badge>
                                            <span className={styles.changeKind}>
                                                {copy.alert.change[change.change] || change.change}
                                            </span>
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </>
                    ) : null}
                </div>
            ) : null}

            <div className={styles.actions}>
                {item.kind === "alert" && item.scan ? (
                    <button type="button" className={styles.action} onClick={() => go(`/scan/${item.scan}/report`)}>
                        {copy.actions.openReport}
                    </button>
                ) : null}
                {item.kind !== "alert" ? (
                    <button type="button" className={styles.action} onClick={() => go("/settings")}>
                        {copy.actions.settings}
                    </button>
                ) : null}
            </div>
        </BellRow>
    );
}
