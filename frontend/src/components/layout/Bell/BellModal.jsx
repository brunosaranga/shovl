import { useEffect, useRef, useState } from "react";
import { useNotifications } from "../../../context/NotificationsContext";
import { useContent } from "../../../hooks/useContent";
import BellIcon from "./BellIcon";
import NeedsItem from "./NeedsItem";
import NewsItem from "./NewsItem";
import styles from "./BellModal.module.css";

// The bell, as a native <dialog> built like the FAQ: above everything, Escape and a click on
// the backdrop close it, focus stays inside. Two groups:
//   needs action   worked out by the API from the current state: can't be read or muted,
//                  and disappears once it's done
//   news           stored: read or unread. The mute quiets the badge, not the list
// The header holds "mark all read", the mute and the close button.
export default function BellModal() {
    const { notifications: copy } = useContent();
    const { bell, status, isOpen, closeBell, muted, markAllRead, setMuted, loadOlder } = useNotifications();
    const dialogRef = useRef(null);
    const closeRef = useRef(null);
    const [problem, setProblem] = useState(false);

    // Focus starts on the close button, as in the FAQ: otherwise the dialog would focus its
    // first button, "mark all read", and light it up as if it had been chosen.
    useEffect(() => {
        const dialog = dialogRef.current;
        if (!dialog) return;
        if (isOpen && !dialog.open) {
            dialog.showModal();
            closeRef.current?.focus();
        }
        if (!isOpen && dialog.open) dialog.close();
    }, [isOpen]);

    const toggleMute = async () => {
        setProblem(false);
        try {
            await setMuted(!muted);
        } catch {
            setProblem(true);
        }
    };

    const older = async () => {
        setProblem(false);
        try {
            await loadOlder();
        } catch {
            setProblem(true);
        }
    };

    const needs = bell?.needs_action || [];
    const news = bell?.news || [];
    const muteLabel = muted ? copy.unmute : copy.mute;

    return (
        <dialog
            ref={dialogRef}
            className={styles.dialog}
            aria-labelledby="bell-title"
            onClose={closeBell}
            onClick={(event) => event.target === event.currentTarget && closeBell()}
        >
            {isOpen ? (
                <>
                    <header className={styles.header}>
                        <h2 id="bell-title" className={styles.title}>
                            {copy.title}
                        </h2>
                        <div className={styles.tools}>
                            <button
                                type="button"
                                className={styles.textButton}
                                onClick={markAllRead}
                                disabled={!bell?.news_unread}
                            >
                                {copy.readAll}
                            </button>
                            <button
                                type="button"
                                className={styles.iconButton}
                                onClick={toggleMute}
                                aria-pressed={muted}
                                aria-label={muteLabel}
                                title={muteLabel}
                                disabled={!bell}
                            >
                                <BellIcon muted={muted} className={styles.icon} />
                            </button>
                            <button
                                ref={closeRef}
                                type="button"
                                className={styles.iconButton}
                                onClick={closeBell}
                                aria-label={copy.close}
                                title={copy.close}
                            >
                                <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.closeIcon}>
                                    <path
                                        d="M5 5l14 14M19 5L5 19"
                                        stroke="currentColor"
                                        strokeWidth="2.6"
                                        strokeLinecap="square"
                                    />
                                </svg>
                            </button>
                        </div>
                    </header>

                    {muted ? <p className={styles.mutedNote}>{copy.mutedNote}</p> : null}

                    <div className={styles.body}>
                        {problem ? (
                            <p className={styles.error} role="alert">
                                {copy.actionFailed}
                            </p>
                        ) : null}
                        {!bell && status === "error" ? (
                            <p className={styles.error} role="alert">
                                {copy.failed}
                            </p>
                        ) : null}
                        {!bell && status !== "error" ? <p className={styles.empty}>{copy.loading}</p> : null}

                        {bell ? (
                            <>
                                <section className={styles.section} aria-labelledby="bell-needs">
                                    <h3 id="bell-needs" className={styles.sectionTitle}>
                                        {copy.needsTitle}
                                        {needs.length ? <span className={styles.count}>{needs.length}</span> : null}
                                    </h3>
                                    {needs.length ? (
                                        <div className={styles.list}>
                                            {needs.map((item) => (
                                                <NeedsItem key={item.key} item={item} />
                                            ))}
                                        </div>
                                    ) : (
                                        <p className={styles.empty}>{copy.needsEmpty}</p>
                                    )}
                                </section>

                                <section className={styles.section} aria-labelledby="bell-news">
                                    <h3 id="bell-news" className={styles.sectionTitle}>
                                        {copy.newsTitle}
                                        {bell.news_unread ? <span className={styles.count}>{bell.news_unread}</span> : null}
                                    </h3>
                                    {news.length ? (
                                        <div className={styles.list}>
                                            {news.map((item) => (
                                                <NewsItem key={item.id} item={item} />
                                            ))}
                                        </div>
                                    ) : (
                                        <p className={styles.empty}>{copy.newsEmpty}</p>
                                    )}
                                    {bell.has_more ? (
                                        <button type="button" className={styles.more} onClick={older}>
                                            {copy.older}
                                        </button>
                                    ) : null}
                                </section>
                            </>
                        ) : null}
                    </div>
                </>
            ) : null}
        </dialog>
    );
}
