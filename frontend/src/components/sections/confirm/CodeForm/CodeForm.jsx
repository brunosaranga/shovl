import { useEffect, useId, useRef, useState } from "react";
import { useSound } from "../../../../context/SoundContext";
import { useContent } from "../../../../hooks/useContent";
import { accountsApi } from "../../../../lib/api";
import { describeError } from "../../../../lib/apiErrors";
import styles from "./CodeForm.module.css";

const DIGITS = 6;

// The code box. Typing or pasting the 6th digit checks it at once; anything that isn't a digit
// is dropped, so "123 456" copied from the email works.
//   POST /api/accounts/email/confirm/ → 200 /me/ body | 400 { code, detail, attempts_left? }
// A wrong code empties the box and plays the error cue. A used-up or expired one hands its
// message to the page (onStale(message)): the page reloads its state, which replaces this box
// with "send a new code", so the message has to be shown there, not here. Once confirmed, the
// button shows "confirmed." for a moment before onConfirmed(the /me/ body) moves the page on.
export default function CodeForm({ onConfirmed, onStale }) {
    const { confirm, errors } = useContent();
    const { play } = useSound();
    const id = useId();
    const inputRef = useRef(null);
    const [digits, setDigits] = useState("");
    const [state, setState] = useState("idle"); // idle | busy | done
    const [problem, setProblem] = useState(null);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    const check = async (code) => {
        setState("busy");
        setProblem(null);
        try {
            const { data } = await accountsApi.confirmEmail(code);
            setState("done");
            setTimeout(() => onConfirmed(data), 900);
        } catch (error) {
            play("error");
            const described = describeError(error, errors);
            setDigits("");
            setState("idle");
            if (described.code === "code_used_up" || described.code === "code_expired") {
                onStale(described.message);
                return;
            }
            setProblem(described.message);
            requestAnimationFrame(() => inputRef.current?.focus());
        }
    };

    const onChange = (event) => {
        const next = event.target.value.replace(/\D/g, "").slice(0, DIGITS);
        setDigits(next);
        if (next.length === DIGITS && state === "idle") check(next);
    };

    const submit = (event) => {
        event.preventDefault();
        if (state !== "idle") return;
        if (digits.length === DIGITS) check(digits);
        else setProblem(errors.codes.code_invalid);
    };

    const errorId = problem ? `${id}-error` : undefined;
    const buttonClasses = [styles.button, state === "done" ? styles.done : "", state !== "idle" ? styles.busy : ""]
        .filter(Boolean)
        .join(" ");

    return (
        <form onSubmit={submit} className={styles.form} noValidate>
            <label htmlFor={id} className={styles.label}>
                {confirm.code.label}
            </label>
            <div className={styles.row}>
                <input
                    ref={inputRef}
                    id={id}
                    className={[styles.input, problem ? styles.invalid : ""].filter(Boolean).join(" ")}
                    value={digits}
                    onChange={onChange}
                    readOnly={state !== "idle"}
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    pattern="[0-9]*"
                    spellCheck={false}
                    aria-invalid={Boolean(problem)}
                    aria-describedby={errorId}
                />
                <button type="submit" className={buttonClasses} disabled={state !== "idle"}>
                    {state === "busy" ? confirm.code.busy : state === "done" ? confirm.code.done : confirm.code.submit}
                </button>
            </div>
            {problem ? (
                <p id={errorId} className={styles.error} role="alert">
                    {problem}
                </p>
            ) : null}
        </form>
    );
}
