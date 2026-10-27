import { useState } from "react";
import TextField from "../../../ui/TextField/TextField";
import Button from "../../../ui/Button/Button";
import { useSound } from "../../../../context/SoundContext";
import { useContent } from "../../../../hooks/useContent";
import { accountsApi } from "../../../../lib/api";
import { describeError } from "../../../../lib/apiErrors";
import styles from "./ChangeAddress.module.css";

// "wrong address? change it": fixes a typo made at sign-up, before the address is confirmed.
// The password is asked again so a device left signed in can't move the account elsewhere.
//   POST /api/accounts/email/change/ → 200 /me/ body + code_sent, send_problem
//                                    | 400 { email: [...] } / { password: [...] } | 429 address_limit
// onDone(the 200 body) once the address has changed, even if the code didn't go out.
export default function ChangeAddress({ onDone, onCancel }) {
    const { confirm, errors } = useContent();
    const { play } = useSound();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState(null); // { message, fields }

    const submit = async (event) => {
        event.preventDefault();
        setBusy(true);
        setProblem(null);
        try {
            const { data } = await accountsApi.changeEmail({ email, password });
            onDone(data);
        } catch (error) {
            play("error");
            setProblem(describeError(error, errors));
            setBusy(false);
        }
    };

    const fields = problem?.fields || {};

    return (
        <form onSubmit={submit} className={styles.form} noValidate>
            <h2 className={styles.title}>{confirm.change.title}</h2>
            <TextField
                label={confirm.change.email}
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                errors={fields.email}
            />
            <TextField
                label={confirm.change.password}
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                hint={confirm.change.passwordHint}
                errors={fields.password}
            />
            {problem?.message ? (
                <p className={styles.error} role="alert">
                    {problem.message}
                </p>
            ) : null}
            <div className={styles.actions}>
                <Button type="submit" variant="small" disabled={busy || !email || !password}>
                    {busy ? confirm.change.busy : confirm.change.submit}
                </Button>
                <Button variant="quiet" onClick={onCancel} disabled={busy}>
                    {confirm.change.cancel}
                </Button>
            </div>
        </form>
    );
}
