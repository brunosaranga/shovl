import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useNotifications } from "../../../context/NotificationsContext";
import { useContent } from "../../../hooks/useContent";
import BellRow from "./BellRow";
import styles from "./BellModal.module.css";

// How long "sure? remove it" waits for the second click before going back.
const CONFIRM_MS = 4000;

// Something that needs the person: a pending domain, a domain that lost verification, a
// watch paused after failed runs. Title and summary come from the API; the buttons:
//   verify   → the verify page in verify-only mode, back here afterwards
//   remove   → asks once more, then DELETE /api/domains/<id>/ (the unverified cache)
//   resume   → POST /api/watches/<id>/resume/
export default function NeedsItem({ item }) {
    const { notifications: copy } = useContent();
    const { closeBell, removeDomain, resumeWatch } = useNotifications();
    const navigate = useNavigate();
    const { pathname } = useLocation();
    const [state, setState] = useState("idle"); // idle | confirm | busy | failed

    useEffect(() => {
        if (state !== "confirm") return undefined;
        const timer = setTimeout(() => setState("idle"), CONFIRM_MS);
        return () => clearTimeout(timer);
    }, [state]);

    const run = async (action) => {
        setState("busy");
        try {
            await action();
        } catch {
            setState("failed");
        }
    };

    const verify = () => {
        closeBell();
        navigate("/verify", { state: { verifyOnly: true, hostname: item.hostname, from: pathname } });
    };

    const remove = () => {
        if (state !== "confirm") {
            setState("confirm");
            return;
        }
        run(() => removeDomain(item.domain_id));
    };

    const busy = state === "busy";
    const removeLabel = busy
        ? copy.actions.removing
        : state === "confirm"
          ? item.watch_ids?.length
              ? copy.actions.removeWatchesConfirm
              : copy.actions.removeConfirm
          : copy.actions.remove;

    return (
        <BellRow title={item.title} info={copy.kinds[item.kind] || copy.needsTitle}>
            <p className={styles.summary}>{item.summary}</p>
            <div className={styles.actions}>
                {item.actions.includes("verify") ? (
                    <button type="button" className={styles.action} onClick={verify} disabled={busy}>
                        {copy.actions.verify}
                    </button>
                ) : null}
                {item.actions.includes("remove") ? (
                    <button
                        type="button"
                        className={[styles.action, styles.danger].join(" ")}
                        onClick={remove}
                        disabled={busy}
                    >
                        {removeLabel}
                    </button>
                ) : null}
                {item.actions.includes("resume") ? (
                    <button
                        type="button"
                        className={styles.action}
                        onClick={() => run(() => resumeWatch(item.watch_id))}
                        disabled={busy}
                    >
                        {busy ? copy.actions.resuming : copy.actions.resume}
                    </button>
                ) : null}
            </div>
            {state === "failed" ? (
                <p className={styles.error} role="alert">
                    {copy.actionFailed}
                </p>
            ) : null}
        </BellRow>
    );
}
