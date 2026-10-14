import { useState } from "react";
import Spinner from "../../../ui/Spinner/Spinner";
import { domainsApi } from "../../../../lib/api";
import { useContent } from "../../../../hooks/useContent";
import styles from "./VerifyAction.module.css";

// The verify button and its states: idle → verifying → verified | failed (→ retry).
//   POST /api/domains/<id>/verify/  → { status: "verified" }  or 400 { status: "failed", detail }
export default function VerifyAction({ domainId, onVerified, onFailed }) {
    const { verify } = useContent();
    const [state, setState] = useState("idle");

    const run = async () => {
        setState("verifying");
        try {
            const { data } = await domainsApi.verify(domainId);
            if (data?.status === "verified") {
                setState("verified");
                setTimeout(() => onVerified?.(), 1200);
                return;
            }
        } catch {
            // 400 = the TXT record isn't visible yet
        }
        setState("failed");
        onFailed?.();
    };

    const busy = state === "verifying" || state === "verified";
    const classes = [styles.button, busy ? styles.busy : "", state === "verified" ? styles.verified : "", state === "failed" ? styles.failed : ""]
        .filter(Boolean)
        .join(" ");

    return (
        <div className={styles.row}>
            <button type="button" onClick={state === "failed" ? () => setState("idle") : run} disabled={busy} className={classes}>
                {state === "failed" ? verify.action.retry : verify.action[state]}
            </button>

            {state === "verifying" ? (
                <div className={styles.spinner}>
                    <Spinner label={verify.spinnerAlt} />
                </div>
            ) : null}
        </div>
    );
}
