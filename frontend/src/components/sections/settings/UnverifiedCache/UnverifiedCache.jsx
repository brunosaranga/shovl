import { useState } from "react";
import { useContent } from "../../../../hooks/useContent";
import { useConfirm } from "../../../../hooks/useConfirm";
import { domainsApi } from "../../../../lib/api";
import { extractHostname } from "../../../../lib/targets";
import { fill } from "../../../../lib/text";
import Breakable from "../../../ui/Breakable/Breakable";
import styles from "./UnverifiedCache.module.css";

// One pending domain, "remove" at the far right. Asks once more first; if a watch is on the
// domain (it lost verification), the question says the watch goes too.
function CacheRow({ domain, watched, onChange }) {
    const { settings } = useContent();
    const copy = settings.cache;
    const [armed, setArmed] = useConfirm();
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState(null);

    const remove = async () => {
        if (!armed) {
            setArmed(true);
            return;
        }
        setArmed(false);
        setBusy(true);
        setProblem(null);
        try {
            await domainsApi.remove(domain.id);
            await onChange();
        } catch {
            setProblem(copy.failed);
            setBusy(false);
        }
    };

    let text = copy.remove;
    if (busy) text = copy.busy;
    else if (armed) text = watched ? copy.removeWatchConfirm : copy.removeConfirm;

    return (
        <li className={styles.item}>
            <span className={styles.host}>
                <Breakable text={domain.hostname} />
            </span>
            <button
                type="button"
                className={styles.remove}
                data-armed={armed || undefined}
                onClick={remove}
                disabled={busy}
            >
                {text}
            </button>
            {problem ? (
                <p className={styles.problem} role="alert">
                    {problem}
                </p>
            ) : null}
        </li>
    );
}

// Settings → domains → the unverified cache: domains started on the verify page but never
// verified, plus any that lost verification. Folded away by default; the count shows on the
// fold. "empty cache" removes them all (DELETE /api/domains/pending/), after asking once more.
//   domains:  the account's pending domains, or null while loading
//   watches:  GET /api/watches/ (to warn when a removal takes a watch with it), or null
//   onChange: reloads Settings' lists and the bell; returns a promise
export default function UnverifiedCache({ domains, watches, onChange }) {
    const { settings } = useContent();
    const copy = settings.cache;
    const [armed, setArmed] = useConfirm();
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState(null);

    const count = domains?.length ?? 0;
    const watchedHosts = new Set((watches || []).map((watch) => extractHostname(watch.target_url)));
    const anyWatched = (domains || []).some((domain) => watchedHosts.has(domain.hostname));

    const emptyAll = async () => {
        if (!armed) {
            setArmed(true);
            return;
        }
        setArmed(false);
        setBusy(true);
        setProblem(null);
        try {
            await domainsApi.removePending();
            await onChange();
        } catch {
            setProblem(copy.failed);
        }
        setBusy(false);
    };

    let emptyText = copy.emptyAll;
    if (busy) emptyText = copy.busy;
    else if (armed) emptyText = fill(anyWatched ? copy.emptyWatchConfirm : copy.emptyConfirm, { n: count });

    return (
        <details className={styles.cache}>
            <summary className={styles.summary}>
                <span>{fill(copy.title, { n: domains === null ? "…" : count })}</span>
                <span className={styles.arrow} aria-hidden="true">
                    →
                </span>
            </summary>
            <div className={styles.body}>
                <p className={styles.lead}>{copy.lead}</p>
                {domains !== null && count === 0 ? <p className={styles.empty}>{copy.empty}</p> : null}
                {count > 0 ? (
                    <ul className={styles.list}>
                        {domains.map((domain) => (
                            <CacheRow
                                key={domain.id}
                                domain={domain}
                                watched={watchedHosts.has(domain.hostname)}
                                onChange={onChange}
                            />
                        ))}
                    </ul>
                ) : null}
                {count > 0 ? (
                    <button
                        type="button"
                        className={styles.emptyAll}
                        data-armed={armed || undefined}
                        onClick={emptyAll}
                        disabled={busy}
                    >
                        {emptyText}
                    </button>
                ) : null}
                {problem ? (
                    <p className={styles.problem} role="alert">
                        {problem}
                    </p>
                ) : null}
            </div>
        </details>
    );
}
