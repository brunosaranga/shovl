import { useNotifications } from "../../../context/NotificationsContext";
import { useContent } from "../../../hooks/useContent";
import { fill } from "../../../lib/text";
import BellIcon from "./BellIcon";
import styles from "./BellButton.module.css";

// Desktop: the bell in the navbar, left of the sound toggle, with the badge. Registered
// accounts only. On mobile the bottom bar is full: "notifications" sits in the account menu
// and a dot on the avatar says there's something new (layout/Navbar/AccountMenu).
export default function BellButton({ className = "" }) {
    const { notifications } = useContent();
    const { enabled, badge, muted, openBell } = useNotifications();
    if (!enabled) return null;

    const label = badge ? fill(notifications.openWithCount, { count: badge }) : notifications.open;

    return (
        <button
            type="button"
            className={[styles.bell, className].filter(Boolean).join(" ")}
            onClick={openBell}
            aria-haspopup="dialog"
            aria-label={label}
            title={label}
        >
            <BellIcon muted={muted} className={styles.icon} />
            {badge ? (
                <span className={styles.badge} aria-hidden="true">
                    {badge > 9 ? "9+" : badge}
                </span>
            ) : null}
        </button>
    );
}
