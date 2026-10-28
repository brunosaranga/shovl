import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import PageBody from "../../components/layout/PageBody/PageBody";
import PageTitle from "../../components/ui/PageTitle/PageTitle";
import Alert from "../../components/ui/Alert/Alert";
import Button from "../../components/ui/Button/Button";
import { useSound } from "../../context/SoundContext";
import { useContent } from "../../hooks/useContent";
import { notificationsApi } from "../../lib/api";
import { describeError } from "../../lib/apiErrors";
import styles from "./EmailOff.module.css";

// Where the "turn these emails off" link in murindzi's emails lands: /email-off?t=<token>.
// The token is signed by the backend (notifications/emails.py) and names one account, so no
// sign-in is needed. Nothing happens on arrival, only when the button is pressed: some mail
// scanners open every link in an email, and that must not switch anyone's emails off.
//   POST /api/notifications/email-off/ { token } → 200 { done } | 400 { code: "link_invalid" }
export default function EmailOff() {
    const { emailOff: copy, errors } = useContent();
    const { play } = useSound();
    const [params] = useSearchParams();
    const token = params.get("t") || "";
    const [state, setState] = useState("idle"); // idle | busy | done
    const [problem, setProblem] = useState(null);

    const turnOff = async () => {
        setState("busy");
        setProblem(null);
        try {
            await notificationsApi.emailOff(token);
            setState("done");
        } catch (error) {
            play("error");
            setProblem(describeError(error, errors).message);
            setState("idle");
        }
    };

    return (
        <>
            <PageMeta title={copy.meta} />
            <NavCenter>
                <PageTitle>{copy.pageTitle}</PageTitle>
            </NavCenter>

            <PageBody width="narrow" gap="lg" top="compact" mono>
                <div className={styles.intro}>
                    <h2 className={styles.title}>{state === "done" ? copy.doneTitle : copy.title}</h2>
                    <p className={styles.lead}>{state === "done" ? copy.done : copy.lead}</p>
                </div>

                {!token ? (
                    <Alert tone="danger" role="alert">
                        <p>{copy.missing}</p>
                    </Alert>
                ) : null}

                {token && state !== "done" ? (
                    <div>
                        <Button onClick={turnOff} disabled={state === "busy"}>
                            {state === "busy" ? copy.button.busy : copy.button.idle}
                        </Button>
                    </div>
                ) : null}

                {problem ? (
                    <Alert tone="danger" role="alert">
                        <p>{problem}</p>
                    </Alert>
                ) : null}

                {state === "done" || !token || problem ? (
                    <p className={styles.help}>
                        <Button variant="quiet" to="/settings">
                            {copy.settings}
                        </Button>
                    </p>
                ) : null}
            </PageBody>
        </>
    );
}
