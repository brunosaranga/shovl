import { Fragment, useEffect, useRef } from "react";
import { useFaq } from "../../../context/FaqContext";
import { useContent } from "../../../hooks/useContent";
import styles from "./FaqModal.module.css";

// In FAQ copy, `backticks` become inline code and {email} becomes a mailto link.
function RichText({ text, email }) {
    return String(text)
        .split(/(`[^`]+`|\{email\})/)
        .map((part, index) => {
            if (part === "{email}") {
                return (
                    <a key={index} href={`mailto:${email}`} className={styles.link}>
                        {email}
                    </a>
                );
            }
            if (part.length > 1 && part.startsWith("`") && part.endsWith("`")) {
                return (
                    <code key={index} className={styles.code}>
                        {part.slice(1, -1)}
                    </code>
                );
            }
            return <Fragment key={index}>{part}</Fragment>;
        });
}

// The FAQ, as a native <dialog>: it sits above everything (navbar included), Escape and a
// click on the backdrop close it, and focus stays inside while it's open.
// Content only renders while open, so every question starts collapsed next time.
export default function FaqModal() {
    const { faq, common } = useContent();
    const { isOpen, closeFaq } = useFaq();
    const dialogRef = useRef(null);

    useEffect(() => {
        const dialog = dialogRef.current;
        if (!dialog) return;
        if (isOpen && !dialog.open) dialog.showModal();
        if (!isOpen && dialog.open) dialog.close();
    }, [isOpen]);

    return (
        <dialog
            ref={dialogRef}
            className={styles.dialog}
            aria-labelledby="faq-title"
            onClose={closeFaq}
            onClick={(event) => event.target === event.currentTarget && closeFaq()}
        >
            {isOpen ? (
                <>
                    <header className={styles.header}>
                        <h2 id="faq-title" className={styles.title}>
                            {faq.title}
                        </h2>
                        <button type="button" className={styles.close} onClick={closeFaq} aria-label={faq.close} title={faq.close}>
                            <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.closeIcon}>
                                <path d="M5 5l14 14M19 5L5 19" stroke="currentColor" strokeWidth="2.6" strokeLinecap="square" />
                            </svg>
                        </button>
                    </header>

                    <div className={styles.body}>
                        {faq.sections.map((section) => (
                            <section key={section.title} className={styles.section}>
                                <h3 className={styles.sectionTitle}>{section.title}</h3>
                                <div className={styles.list}>
                                    {section.items.map((item) => (
                                        <details key={item.q} className={styles.item}>
                                            <summary className={styles.question}>
                                                <span>{item.q}</span>
                                                <span className={styles.marker} aria-hidden="true" />
                                            </summary>
                                            <p className={styles.answer}>
                                                <RichText text={item.a} email={common.contactEmail} />
                                            </p>
                                        </details>
                                    ))}
                                </div>
                            </section>
                        ))}
                    </div>

                    <footer className={styles.footer}>
                        <RichText text={faq.footer} email={common.contactEmail} />
                    </footer>
                </>
            ) : null}
        </dialog>
    );
}
