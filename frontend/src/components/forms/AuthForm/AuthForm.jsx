import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import TextField from "../../ui/TextField/TextField";
import Checkbox from "../../ui/Checkbox/Checkbox";
import LinkedText from "../../ui/LinkedText/LinkedText";
import { useSession } from "../../../context/SessionContext";
import { useSound } from "../../../context/SoundContext";
import { useContent } from "../../../hooks/useContent";
import { describeError } from "../../../lib/apiErrors";
import styles from "./AuthForm.module.css";

// Email + password, for both tabs.
//   register: password rules hint, consent tick, server password errors listed under the field,
//             and an optional, unticked "email me once at launch" (the launch list: it only
//             counts once the account's email code is typed, backend waitlist/).
//             A guest is upgraded in place (SessionContext.register) and keeps their scans.
//   signin:   a guest's scans move to the account they sign in to.
// On success the session becomes "registered" and the Auth page redirects; no callback needed.
// Sign in also offers "forgot your password?" (pages/ResetPassword), carrying the address typed
// so far and where the visitor was going.
export default function AuthForm({ mode, notice, onSuccess }) {
    const { auth, errors, waitlist: launchList } = useContent();
    const { status, signIn, register } = useSession();
    const location = useLocation();
    const { play } = useSound();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [consent, setConsent] = useState(false);
    const [launch, setLaunch] = useState(false);
    const [problem, setProblem] = useState(null); // { message, fields }
    const [busy, setBusy] = useState(false);

    const isRegister = mode === "register";
    const isGuest = status === "guest";

    const submit = async (event) => {
        event.preventDefault();
        if (isRegister && !consent) return;

        setProblem(null);
        setBusy(true);
        try {
            if (isRegister) {
                await register({ email, password, waitlist: launch });
            } else {
                await signIn({ email, password });
            }
            onSuccess?.();
        } catch (error) {
            play("error");
            setProblem(describeError(error, errors));
            setBusy(false);
        }
    };

    const fields = problem?.fields || {};
    const guestNote = isGuest ? (isRegister ? auth.guest.register : auth.guest.signin) : null;

    return (
        <form onSubmit={submit} className={styles.form} noValidate>
            {notice ? <p className={styles.note}>{notice}</p> : null}
            {guestNote ? <p className={styles.note}>{guestNote}</p> : null}

            <TextField
                label={auth.fields.email}
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder={auth.fields.emailPlaceholder}
                required
                errors={fields.email}
            />

            <TextField
                label={auth.fields.password}
                type="password"
                autoComplete={isRegister ? "new-password" : "current-password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                hint={isRegister ? auth.fields.passwordHint : undefined}
                errors={fields.password}
            />

            {!isRegister ? (
                <Link to="/reset-password" state={{ ...(location.state || {}), email }} className={styles.forgot}>
                    {auth.forgot}
                </Link>
            ) : null}

            {isRegister ? <Checkbox label={<LinkedText text={auth.consent} newTab />} checked={consent} onChange={setConsent} /> : null}
            {isRegister ? <Checkbox label={launchList.consent.text} checked={launch} onChange={setLaunch} /> : null}

            {problem?.message ? (
                <p className={styles.error} role="alert">
                    {problem.message}
                </p>
            ) : null}

            <button type="submit" disabled={busy || (isRegister && !consent)} className={styles.submit}>
                {busy ? auth.submit.busy : isRegister ? auth.submit.register : auth.submit.signin}
            </button>
        </form>
    );
}
