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
import { waitlistApi } from "../../lib/api";
import { describeError } from "../../lib/apiErrors";
import styles from "./Waitlist.module.css";

// Where the launch list's email buttons land (backend waitlist/):
//   /waitlist/confirm?t=<token>   "confirm": the link in the confirmation email (48 hours, once)
//   /waitlist/leave?t=<token>     "remove me": in every email from the list
// Both work signed out, from any browser. Nothing happens on arrival, only when the button is
// pressed: some mail scanners open every link in an email, and that must not confirm or remove
// anyone.
//   POST /api/waitlist/confirm/ or /leave/ { token } → 200 { done } | 400 { code: "link_invalid" }
export default function Waitlist({ mode }) {
    const { waitlist, errors } = useContent();
    const copy = waitlist.pages;
    const step = copy[mode];
    const { play } = useSound();
    const [params] = useSearchParams();
    const token = params.get("t") || "";
    const [state, setState] = useState("idle"); // idle | busy | done
    const [problem, setProblem] = useState(null);

    const press = async () => {
        setState("busy");
        setProblem(null);
        try {
            await (mode === "leave" ? waitlistApi.leave(token) : waitlistApi.confirm(token));
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
                    <h2 className={styles.title}>{state === "done" ? step.doneTitle : step.title}</h2>
                    <p className={styles.lead}>{state === "done" ? step.done : step.lead}</p>
                </div>

                {!token ? (
                    <Alert tone="danger" role="alert">
                        <p>{copy.missing}</p>
                    </Alert>
                ) : null}

                {token && state !== "done" ? (
                    <div>
                        <Button onClick={press} disabled={state === "busy"}>
                            {state === "busy" ? step.busy : step.button}
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
                        <Button variant="quiet" to="/">
                            {copy.home}
                        </Button>
                    </p>
                ) : null}
            </PageBody>
        </>
    );
}
