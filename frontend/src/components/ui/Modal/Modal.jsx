import { useEffect, useRef } from "react";
import styles from "./Modal.module.css";

// A small blocking question ("stop this scan?"). Escape or the backdrop cancels.
export default function Modal({ open, title, children, actions, onClose }) {
    const panelRef = useRef(null);

    useEffect(() => {
        if (!open) return undefined;
        panelRef.current?.querySelector("button")?.focus();
        const onKey = (event) => event.key === "Escape" && onClose?.();
        document.addEventListener("keydown", onKey);
        return () => document.removeEventListener("keydown", onKey);
    }, [open, onClose]);

    if (!open) return null;

    return (
        <div className={styles.backdrop} onMouseDown={(event) => event.target === event.currentTarget && onClose?.()}>
            <div className={styles.panel} role="dialog" aria-modal="true" aria-labelledby="modal-title" ref={panelRef}>
                <h2 id="modal-title" className={styles.title}>
                    {title}
                </h2>
                {children ? <div className={styles.body}>{children}</div> : null}
                {actions ? <div className={styles.actions}>{actions}</div> : null}
            </div>
        </div>
    );
}
