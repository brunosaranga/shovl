import { useEffect, useRef } from "react";
import styles from "./Terminal.module.css";

// Dark log window. Scrolls to the newest line as lines arrive and stays scrollable.
export default function Terminal({ lines = [], footer, footerTone = "success" }) {
    const scrollRef = useRef(null);

    useEffect(() => {
        const element = scrollRef.current;
        if (element) element.scrollTop = element.scrollHeight;
    }, [lines, footer]);

    return (
        <div className={styles.terminal} ref={scrollRef} role="log" aria-live="polite">
            {lines.map((line, index) => (
                <div key={index} className={index === lines.length - 1 ? styles.latest : styles.line}>
                    {line}
                </div>
            ))}
            {footer ? <div className={styles[footerTone]}>{footer}</div> : null}
        </div>
    );
}
