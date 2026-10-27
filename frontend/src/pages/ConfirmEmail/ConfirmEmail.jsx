import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import PageBody from "../../components/layout/PageBody/PageBody";
import PageTitle from "../../components/ui/PageTitle/PageTitle";
import Alert from "../../components/ui/Alert/Alert";
import Button from "../../components/ui/Button/Button";
import CodeForm from "../../components/sections/confirm/CodeForm/CodeForm";
import ChangeAddress from "../../components/sections/confirm/ChangeAddress/ChangeAddress";
import { useSession } from "../../context/SessionContext";
import { useSound } from "../../context/SoundContext";
import { useContent } from "../../hooks/useContent";
import { useCountdown } from "../../hooks/useCountdown";
import { accountsApi } from "../../lib/api";
import { describeError } from "../../lib/apiErrors";
import { fill, formatDate } from "../../lib/text";
import styles from "./ConfirmEmail.module.css";

// The code screen. Every page but the public ones sends an account whose email isn't confirmed
// here (AccessGate), with where it was going in location.state; once the code is right the
// session turns "registered" and AccessGate sends it on there (or to the dashboard).
//
// What it shows comes from /me/'s `confirmation` (backend accounts/confirmation.py):
//   a code waiting (code_sent_at)  → the code box, "send a new code" (after resend_in seconds)
//   no code yet                    → "email me the code": accounts from before confirmation
//                                    existed, or a code that expired, was used up or never went out
//   confirm_by                     → the deadline, for accounts that signed up
// "wrong address? change it" fixes a typo; "not you? log out" leaves.
export default function ConfirmEmail() {
    const { confirm, errors } = useContent();
    const { user, applyUser, refreshUser, signOut } = useSession();
    const { play } = useSound();
    const navigate = useNavigate();
    const [sending, setSending] = useState(false);
    const [notice, setNotice] = useState(null); // { tone: "info" | "danger", text }
    const [changing, setChanging] = useState(false);

    const state = user?.confirmation ?? null;
    const codeWaiting = Boolean(state?.code_sent_at);
    const wait = useCountdown(state && user ? user.receivedAt + state.resend_in * 1000 : null);

    const send = async () => {
        setSending(true);
        setNotice(null);
        try {
            const { data } = await accountsApi.sendCode();
            applyUser(data);
            if (codeWaiting) setNotice({ tone: "info", text: confirm.resend.done });
        } catch (error) {
            play("error");
            const described = describeError(error, errors);
            setNotice({ tone: "danger", text: described.message });
            if (described.code === "code_cooldown") refreshUser();
        } finally {
            setSending(false);
        }
    };

    const changed = (data) => {
        applyUser(data);
        setChanging(false);
        setNotice(
            data.code_sent
                ? { tone: "info", text: fill(confirm.change.done, { email: data.email }) }
                : {
                      tone: "danger",
                      text: fill(confirm.change.notSent, {
                          email: data.email,
                          reason: data.send_problem?.detail || errors.codes.email_failed,
                      }),
                  }
        );
    };

    // The code ran out (used up, or expired): say why the box went, and offer a new code.
    const stale = (message) => {
        setNotice({ tone: "danger", text: message });
        refreshUser();
    };

    const leave = () => {
        signOut();
        navigate("/");
    };

    const sendLabel = sending
        ? confirm.send.busy
        : wait
          ? fill(confirm.resend.wait, { seconds: wait })
          : codeWaiting
            ? confirm.resend.idle
            : confirm.send.idle;

    return (
        <>
            <PageMeta title={confirm.meta} />
            <NavCenter>
                <PageTitle>{confirm.pageTitle}</PageTitle>
            </NavCenter>

            <PageBody width="narrow" gap="lg" top="compact" mono>
                {!user ? (
                    <p className={styles.status}>{confirm.loading}</p>
                ) : (
                    <>
                        <div className={styles.intro}>
                            <h2 className={styles.title}>{confirm.title}</h2>
                            <p className={styles.lead}>
                                <WithEmail template={codeWaiting ? confirm.sent : confirm.notSent} email={user.email} />
                            </p>
                            <p className={styles.note}>{confirm.why}</p>
                            {state?.confirm_by ? (
                                <p className={styles.note}>{fill(confirm.deadline, { date: formatDate(state.confirm_by) })}</p>
                            ) : null}
                        </div>

                        {codeWaiting ? (
                            <CodeForm key={state.code_sent_at} onConfirmed={applyUser} onStale={stale} />
                        ) : (
                            <div>
                                <Button onClick={send} disabled={sending || wait > 0}>
                                    {sendLabel}
                                </Button>
                            </div>
                        )}

                        {notice ? (
                            <Alert tone={notice.tone} role={notice.tone === "danger" ? "alert" : "status"}>
                                <p>{notice.text}</p>
                            </Alert>
                        ) : null}

                        <div className={styles.links}>
                            {codeWaiting ? (
                                <p className={styles.help}>
                                    {confirm.spam}{" "}
                                    <Button variant="quiet" onClick={send} disabled={sending || wait > 0}>
                                        {sendLabel}
                                    </Button>
                                </p>
                            ) : null}

                            {changing ? (
                                <ChangeAddress onDone={changed} onCancel={() => setChanging(false)} />
                            ) : (
                                <p className={styles.help}>
                                    <Button
                                        variant="quiet"
                                        onClick={() => {
                                            setChanging(true);
                                            setNotice(null);
                                        }}
                                    >
                                        {confirm.change.toggle}
                                    </Button>
                                </p>
                            )}

                            <p className={styles.help}>
                                <Button variant="quiet" onClick={leave}>
                                    {confirm.signOut}
                                </Button>
                            </p>
                        </div>
                    </>
                )}
            </PageBody>
        </>
    );
}

// "we sent a code to {email}" with the address set apart, like the target on the verify page.
function WithEmail({ template, email }) {
    const [before, after = ""] = template.split("{email}");
    return (
        <>
            {before}
            <strong className={styles.badge}>{email}</strong>
            {after}
        </>
    );
}
