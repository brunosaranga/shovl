import { useId, useState } from "react";
import Button from "../../../ui/Button/Button";
import { useContent } from "../../../../hooks/useContent";
import { scansApi } from "../../../../lib/api";
import { fill } from "../../../../lib/text";
import styles from "./ReportFeedback.module.css";

const COMMENT_MAX = 500; // ScanFeedback.COMMENT_MAX_LENGTH in the backend
const PAY_CHOICES = ["yes", "maybe", "no"];

// Whether the person skipped the question or finished with it, per scan, in this browser.
// "skipped" hides the block on this report; "done" folds it into a thank-you line.
const storageKey = (scanId) => `shovl.feedback.${scanId}`;

function readClosed(scanId) {
    try {
        return localStorage.getItem(storageKey(scanId));
    } catch {
        return null;
    }
}

function writeClosed(scanId, value) {
    try {
        if (value) localStorage.setItem(storageKey(scanId), value);
        else localStorage.removeItem(storageKey(scanId));
    } catch {
        // storage unavailable: the choice holds until the page closes
    }
}

// "was this report useful?" at the bottom of a finished report. Entirely optional: one click
// answers it, "skip" hides it, and nothing else on the page waits for it. After the first
// answer, two optional extras: a comment, and whether they'd pay for weekly scans with an
// email when something changes. Each is saved as soon as it's given
// (POST /api/scans/<id>/feedback/; the admin shows answers next to what the report showed).
// Render it with a key per scan (pages/Report: `feedback-<id>`), so another report starts
// fresh. The key must differ from its siblings' keys.
export default function ReportFeedback({ scanId, initial = null }) {
    const { report } = useContent();
    const copy = report.feedback;
    const commentId = useId();

    const [answer, setAnswer] = useState(initial); // { useful, comment, would_pay } from the API
    const [closed, setClosed] = useState(() => readClosed(scanId));
    const [draft, setDraft] = useState(initial?.comment || "");
    const [sending, setSending] = useState(null); // which part is being saved
    const [error, setError] = useState(null);

    const close = (value) => {
        writeClosed(scanId, value);
        setClosed(value);
    };

    const save = async (part, body) => {
        setSending(part);
        setError(null);
        try {
            const { data } = await scansApi.feedback(scanId, body);
            setAnswer(data);
            if (part === "comment") setDraft(data.comment || "");
            return data;
        } catch (failure) {
            setError(failure.response?.status === 429 ? copy.errors.tooMany : copy.errors.failed);
            return null;
        } finally {
            setSending(null);
        }
    };

    const answerUseful = (useful) => save("useful", { useful });

    const sendComment = async (event) => {
        event.preventDefault();
        const data = await save("comment", { comment: draft });
        if (data?.comment && data.would_pay) close("done");
    };

    const answerPay = async (choice) => {
        const data = await save("pay", { would_pay: choice });
        if (data?.would_pay && data.comment) close("done");
    };

    if (closed === "skipped" && !answer) return null;

    if (closed && answer) {
        return (
            <p className={`meta-line ${styles.thanks}`}>
                {copy.thanks}{" "}
                <button type="button" className={styles.quiet} onClick={() => close(null)}>
                    {copy.change}
                </button>
            </p>
        );
    }

    const busy = sending !== null;
    const commentChanged = draft.trim() !== (answer?.comment || "");

    return (
        <section className={styles.card} aria-labelledby="feedback-title">
            {!answer ? (
                <>
                    <div className={styles.head}>
                        <h3 id="feedback-title" className={styles.title}>
                            {copy.title}
                        </h3>
                        <button type="button" className={styles.quiet} onClick={() => close("skipped")}>
                            {copy.skip}
                        </button>
                    </div>
                    <p className={styles.lead}>{copy.lead}</p>
                    <div className={styles.choices}>
                        <Button variant="small" onClick={() => answerUseful(true)} disabled={busy}>
                            {copy.yes}
                        </Button>
                        <Button variant="small" onClick={() => answerUseful(false)} disabled={busy}>
                            {copy.no}
                        </Button>
                    </div>
                </>
            ) : (
                <>
                    <div className={styles.head}>
                        <h3 id="feedback-title" className={styles.title}>
                            {copy.followUp}
                        </h3>
                        <button type="button" className={styles.quiet} onClick={() => close("done")}>
                            {copy.done}
                        </button>
                    </div>

                    <form className={styles.part} onSubmit={sendComment}>
                        <label htmlFor={commentId} className={styles.question}>
                            {copy.comment.label}
                        </label>
                        <textarea
                            id={commentId}
                            className={styles.textarea}
                            rows={3}
                            maxLength={COMMENT_MAX}
                            placeholder={copy.comment.placeholder}
                            value={draft}
                            onChange={(event) => setDraft(event.target.value)}
                        />
                        <div className={styles.row}>
                            <Button variant="small" type="submit" disabled={busy || !draft.trim() || !commentChanged}>
                                {sending === "comment" ? copy.sending : copy.comment.send}
                            </Button>
                            <span className={styles.count} aria-live="polite">
                                {answer.comment && !commentChanged ? copy.comment.sent : fill(copy.comment.count, { n: draft.length, max: COMMENT_MAX })}
                            </span>
                        </div>
                    </form>

                    <div className={styles.part} role="group" aria-labelledby="feedback-pay">
                        <p id="feedback-pay" className={styles.question}>
                            {copy.pay.question}
                        </p>
                        <div className={styles.choices}>
                            {PAY_CHOICES.map((choice) => (
                                <button
                                    key={choice}
                                    type="button"
                                    className={answer.would_pay === choice ? `${styles.choice} ${styles.picked}` : styles.choice}
                                    aria-pressed={answer.would_pay === choice}
                                    onClick={() => answerPay(choice)}
                                    disabled={busy}
                                >
                                    {copy.pay[choice]}
                                </button>
                            ))}
                        </div>
                    </div>
                </>
            )}

            {error ? (
                <p className={styles.error} role="alert">
                    {error}
                </p>
            ) : null}
        </section>
    );
}
