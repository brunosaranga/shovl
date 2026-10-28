import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import PageBody from "../../components/layout/PageBody/PageBody";
import PageTitle from "../../components/ui/PageTitle/PageTitle";
import Alert from "../../components/ui/Alert/Alert";
import Button from "../../components/ui/Button/Button";
import TextField from "../../components/ui/TextField/TextField";
import { useSession } from "../../context/SessionContext";
import { useSound } from "../../context/SoundContext";
import { useContent } from "../../hooks/useContent";
import { useCountdown } from "../../hooks/useCountdown";
import { accountsApi } from "../../lib/api";
import { describeError } from "../../lib/apiErrors";
import { isPracticeTarget } from "../../lib/targets";
import { fill } from "../../lib/text";
import styles from "./ResetPassword.module.css";

// A forgotten password, signed out (backend accounts/reset.py):
//   1. the address → POST /password/reset/: the same answer whether or not it has an account
//   2. the code from the email + a new password → POST /password/reset/confirm/: signs in
//      (every other session is signed out), then on to where the visitor was going, like sign-in
// Reached from "forgot your password?" on the sign-in tab, which passes the address typed so far
// and the sign-in page's own state (from, fromState, pendingScan) in location.state.

// Where to go once signed in: the same rules as the sign-in page (pages/Auth).
function destination(state) {
    if (state?.from) return { to: state.from, state: state.fromState ?? undefined };
    const pending = state?.pendingScan;
    if (pending?.url) return { to: isPracticeTarget(pending.url) ? "/scan/running" : "/verify", state: pending };
    return { to: "/dashboard" };
}

export default function ResetPassword() {
    const { reset: copy, errors } = useContent();
    const { resetPassword } = useSession();
    const { play } = useSound();
    const navigate = useNavigate();
    const location = useLocation();
    const state = location.state || {};

    const [step, setStep] = useState("ask"); // ask | code
    const [email, setEmail] = useState(state.email || "");
    const [code, setCode] = useState("");
    const [password, setPassword] = useState("");
    const [busy, setBusy] = useState(null); // "ask" | "resend" | "reset" | "done" | null
    const [problem, setProblem] = useState(null); // { message, fields }
    const [notice, setNotice] = useState(null);
    const [resendAt, setResendAt] = useState(null);
    const wait = useCountdown(resendAt);

    const fail = (error) => {
        play("error");
        const described = describeError(error, errors);
        setProblem(described);
        return described;
    };

    // Step 1, and "send a new code" on step 2.
    const ask = async (event, again = false) => {
        event?.preventDefault();
        setBusy(again ? "resend" : "ask");
        setProblem(null);
        setNotice(null);
        try {
            const { data } = await accountsApi.requestReset(email);
            setResendAt(Date.now() + (data.resend_in || 60) * 1000);
            setStep("code");
            if (again) setNotice(copy.resend.done);
        } catch (error) {
            fail(error);
            if (error.response?.data?.retry_after) setResendAt(Date.now() + error.response.data.retry_after * 1000);
        }
        setBusy(null);
    };

    const submit = async (event) => {
        event.preventDefault();
        setBusy("reset");
        setProblem(null);
        setNotice(null);
        try {
            await resetPassword({ email, code, password });
            setBusy("done");
            const next = destination(state);
            setTimeout(() => navigate(next.to, { state: next.state, replace: true }), 900);
        } catch (error) {
            // Only a problem with the code empties the box. A weak password never used the code
            // up (the backend checks the password first), so it stays for the next try.
            if (fail(error).code?.startsWith("code_")) setCode("");
            setBusy(null);
        }
    };

    const fields = problem?.fields || {};
    const [before, after = ""] = copy.code.lead.split("{email}");
    const resendLabel =
        busy === "resend" ? copy.resend.busy : wait ? fill(copy.resend.wait, { seconds: wait }) : copy.resend.idle;

    return (
        <>
            <PageMeta title={copy.meta} />
            <NavCenter>
                <PageTitle>{copy.pageTitle}</PageTitle>
            </NavCenter>

            <PageBody width="narrow" gap="lg" top="compact" mono>
                {step === "ask" ? (
                    <>
                        <div className={styles.intro}>
                            <h2 className={styles.title}>{copy.ask.title}</h2>
                            <p className={styles.lead}>{copy.ask.lead}</p>
                        </div>
                        <form onSubmit={ask} className={styles.form} noValidate>
                            <TextField
                                label={copy.ask.email}
                                type="email"
                                autoComplete="email"
                                value={email}
                                onChange={(event) => setEmail(event.target.value)}
                                placeholder={copy.ask.emailPlaceholder}
                                required
                                errors={fields.email}
                            />
                            {problem?.message ? (
                                <p className={styles.error} role="alert">
                                    {problem.message}
                                </p>
                            ) : null}
                            <div>
                                <Button type="submit" disabled={busy === "ask" || !email.trim()}>
                                    {busy === "ask" ? copy.ask.busy : copy.ask.submit}
                                </Button>
                            </div>
                        </form>
                    </>
                ) : (
                    <>
                        <div className={styles.intro}>
                            <h2 className={styles.title}>{copy.code.title}</h2>
                            <p className={styles.lead}>
                                {before}
                                <strong className={styles.badge}>{email.trim().toLowerCase()}</strong>
                                {after}
                            </p>
                            <p className={styles.note}>{copy.code.note}</p>
                        </div>
                        <form onSubmit={submit} className={styles.form} noValidate>
                            <TextField
                                label={copy.code.code}
                                value={code}
                                onChange={(event) => setCode(event.target.value.replace(/[^\d\s-]/g, "").slice(0, 9))}
                                inputMode="numeric"
                                autoComplete="one-time-code"
                                spellCheck={false}
                                className={styles.codeField}
                                required
                            />
                            <TextField
                                label={copy.code.password}
                                type="password"
                                autoComplete="new-password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                hint={copy.code.passwordHint}
                                required
                                errors={fields.password}
                            />
                            {problem?.message ? (
                                <p className={styles.error} role="alert">
                                    {problem.message}
                                </p>
                            ) : null}
                            <div>
                                <Button
                                    type="submit"
                                    className={busy === "done" ? styles.done : ""}
                                    disabled={busy !== null || !code.trim() || !password}
                                >
                                    {busy === "reset" ? copy.code.busy : busy === "done" ? copy.code.done : copy.code.submit}
                                </Button>
                            </div>
                        </form>

                        {notice ? (
                            <Alert tone="info" role="status">
                                <p>{notice}</p>
                            </Alert>
                        ) : null}

                        <div className={styles.links}>
                            <p className={styles.help}>
                                {copy.spam}{" "}
                                <Button variant="quiet" onClick={() => ask(null, true)} disabled={busy !== null || wait > 0}>
                                    {resendLabel}
                                </Button>
                            </p>
                            <p className={styles.help}>
                                <Button
                                    variant="quiet"
                                    onClick={() => {
                                        setStep("ask");
                                        setProblem(null);
                                        setNotice(null);
                                        setCode("");
                                    }}
                                    disabled={busy !== null}
                                >
                                    {copy.other}
                                </Button>
                            </p>
                        </div>
                    </>
                )}

                <p className={styles.help}>
                    <Link to="/signin" state={state} className={styles.back}>
                        {copy.back}
                    </Link>
                </p>
            </PageBody>
        </>
    );
}
