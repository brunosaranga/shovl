import { Link } from "react-router-dom";
import Button from "../../../ui/Button/Button";
import Checkbox from "../../../ui/Checkbox/Checkbox";
import { useContent } from "../../../../hooks/useContent";
import { PRACTICE_TARGETS } from "../../../../lib/targets";
import { fill } from "../../../../lib/text";
import styles from "./LaunchPanel.module.css";

// The "dig deeper" button, with a small card for what goes with it:
//   the consent tick (only when nobody is signed in: ticking it is what creates the guest session),
//   how many scans are left, any reason the scan couldn't start, and (for anyone not
//   registered) one-click practice targets that fill the URL box.
// Desktop: the card floats just above the button. Mobile: just below it.
export default function LaunchPanel({
    onLaunch,
    busy,
    showConsent,
    consent,
    onConsentChange,
    consentError,
    consentRef,
    allowanceText,
    error,
    showExamples,
    onPickExample,
}) {
    const { landing } = useContent();
    const hasCard = showConsent || allowanceText || error || showExamples;

    return (
        <div className={styles.launch}>
            <Button onClick={onLaunch} disabled={busy}>
                {busy ? landing.starting : landing.cta}
            </Button>

            {hasCard ? (
                <div className={styles.card}>
                    {showConsent ? (
                        <Checkbox
                            label={landing.consent}
                            checked={consent}
                            onChange={onConsentChange}
                            invalid={consentError}
                            inputRef={consentRef}
                        />
                    ) : null}
                    {consentError ? <p className={styles.error}>{landing.consentRequired}</p> : null}
                    {error ? (
                        <p className={styles.error} role="alert">
                            {error.message}{" "}
                            {error.code === "too_many_sessions" ? (
                                <Link to="/signin" state={{ mode: "register" }}>
                                    {landing.createAccount}
                                </Link>
                            ) : null}
                        </p>
                    ) : null}
                    {allowanceText ? <p className={styles.allowance}>{allowanceText}</p> : null}
                    {showExamples ? (
                        <div className={styles.examples}>
                            <span className={styles.allowance}>{landing.tryLabel}</span>
                            {PRACTICE_TARGETS.map((target) => {
                                const shown = target.example.replace(/^https?:\/\//, "");
                                return (
                                    <button
                                        key={target.host}
                                        type="button"
                                        className={styles.example}
                                        onClick={() => onPickExample(target.example)}
                                        aria-label={fill(landing.tryAria, { url: shown })}
                                    >
                                        {shown}
                                    </button>
                                );
                            })}
                        </div>
                    ) : null}
                </div>
            ) : null}
        </div>
    );
}
