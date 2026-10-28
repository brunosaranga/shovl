import { useEffect, useRef, useState } from "react";
import TextField from "../../../ui/TextField/TextField";
import Button from "../../../ui/Button/Button";
import Alert from "../../../ui/Alert/Alert";
import LinkedText from "../../../ui/LinkedText/LinkedText";
import { useSession } from "../../../../context/SessionContext";
import { useSound } from "../../../../context/SoundContext";
import { useContent } from "../../../../hooks/useContent";
import { waitlistApi } from "../../../../lib/api";
import { describeError } from "../../../../lib/apiErrors";
import styles from "./WaitlistModal.module.css";

// "want to hear when xikomu launches?": the launch list (backend waitlist/), asked once per
// browser after a completed scan (pages/Report, lib/waitlistSeen.js). A native <dialog> like
// the FAQ: Escape, the close button, "no thanks" and the backdrop all close it.
//
// The promise next to the button is content/en/waitlist.js consent.text, word for word, and
// its version goes with the request: the backend refuses a version that isn't its own.
// Nothing is on the list until the button in the confirmation email is pressed, except for a
// confirmed account using its own address (the server answers "confirmed" then).
// `website` is a field people never see: the server ignores any request that fills it.
export default function WaitlistModal({ open, onClose }) {
    const { waitlist: copy, errors } = useContent();
    const { user, isRegistered } = useSession();
    const { play } = useSound();
    const dialogRef = useRef(null);

    const [firstName, setFirstName] = useState("");
    const [email, setEmail] = useState(null); // null until the visitor types in the field
    const [website, setWebsite] = useState("");
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState(null); // { message, fields }
    const [result, setResult] = useState(null); // { status, detail }

    useEffect(() => {
        const dialog = dialogRef.current;
        if (!dialog) return;
        if (open && !dialog.open) {
            dialog.showModal();
            // Straight to the name with a mouse or trackpad; on touch screens a keyboard popping
            // up unasked would cover the question, so focus stays where the browser puts it.
            if (window.matchMedia?.("(pointer: fine)").matches) dialog.querySelector("input")?.focus();
        }
        if (!open && dialog.open) dialog.close();
    }, [open]);

    // A signed-in account's address, until the visitor types their own.
    const accountEmail = isRegistered && user?.email ? user.email : "";
    const shownEmail = email ?? accountEmail;

    const submit = async (event) => {
        event.preventDefault();
        setBusy(true);
        setProblem(null);
        try {
            const { data } = await waitlistApi.join({
                first_name: firstName,
                email: shownEmail,
                consent_version: copy.consent.version,
                website,
            });
            setResult({ status: data.status, detail: data.detail });
        } catch (error) {
            play("error");
            setProblem(describeError(error, errors));
        } finally {
            setBusy(false);
        }
    };

    const fields = problem?.fields || {};
    const formProblem = problem?.message || fields.consent?.[0] || null;

    return (
        <dialog
            ref={dialogRef}
            className={styles.dialog}
            aria-labelledby="waitlist-title"
            onClose={onClose}
            onClick={(event) => event.target === event.currentTarget && onClose()}
        >
            {open ? (
                <>
                    <header className={styles.header}>
                        <h2 id="waitlist-title" className={styles.title}>
                            {result ? (result.status === "confirmed" ? copy.modal.confirmedTitle : copy.modal.pendingTitle) : copy.modal.title}
                        </h2>
                        <button type="button" className={styles.close} onClick={onClose} aria-label={copy.modal.close} title={copy.modal.close}>
                            <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.closeIcon}>
                                <path d="M5 5l14 14M19 5L5 19" stroke="currentColor" strokeWidth="2.6" strokeLinecap="square" />
                            </svg>
                        </button>
                    </header>

                    {result ? (
                        <div className={styles.body}>
                            <p className={styles.lead} role="status">
                                {result.detail}
                            </p>
                            <div className={styles.actions}>
                                <Button variant="small" onClick={onClose}>
                                    {copy.modal.close}
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <form className={styles.body} onSubmit={submit} noValidate>
                            <p className={styles.lead}>{copy.modal.lead}</p>

                            <TextField
                                label={copy.modal.name}
                                autoComplete="given-name"
                                maxLength={50}
                                value={firstName}
                                onChange={(event) => setFirstName(event.target.value)}
                                placeholder={copy.modal.namePlaceholder}
                                required
                                errors={fields.first_name}
                            />
                            <TextField
                                label={copy.modal.email}
                                type="email"
                                autoComplete="email"
                                value={shownEmail}
                                onChange={(event) => setEmail(event.target.value)}
                                placeholder={copy.modal.emailPlaceholder}
                                required
                                errors={fields.email}
                            />

                            {/* For bots only: off screen, out of the tab order, hidden from screen readers. */}
                            <div className={styles.trap} aria-hidden="true">
                                <label>
                                    website
                                    <input
                                        type="text"
                                        name="website"
                                        tabIndex={-1}
                                        autoComplete="off"
                                        value={website}
                                        onChange={(event) => setWebsite(event.target.value)}
                                    />
                                </label>
                            </div>

                            <p className={styles.consent}>{copy.consent.text}</p>

                            {formProblem ? (
                                <Alert tone="danger" role="alert">
                                    <p>{formProblem}</p>
                                </Alert>
                            ) : null}

                            <div className={styles.actions}>
                                <Button type="submit" disabled={busy}>
                                    {busy ? copy.modal.busy : copy.modal.submit}
                                </Button>
                                <Button variant="quiet" onClick={onClose}>
                                    {copy.modal.skip}
                                </Button>
                            </div>

                            <p className={styles.privacy}>
                                <LinkedText text={copy.modal.privacy} newTab />
                            </p>
                        </form>
                    )}
                </>
            ) : null}
        </dialog>
    );
}
