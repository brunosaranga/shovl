import { Link } from "react-router-dom";
import Button from "../../../ui/Button/Button";
import Checkbox from "../../../ui/Checkbox/Checkbox";
import { useContent } from "../../../../hooks/useContent";
import styles from "./LaunchPanel.module.css";

// The "dig deeper" button, with a small card for what goes with it:
//   the consent tick (only when nobody is signed in: ticking it is what creates the guest session),
//   how many scans are left, and any reason the scan couldn't start.
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
}) {
    const { landing } = useContent();
    const hasCard = showConsent || allowanceText || error;

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
                </div>
            ) : null}
        </div>
    );
}
