import { useFaq } from "../../../context/FaqContext";
import { useContent } from "../../../hooks/useContent";
import styles from "./FaqButton.module.css";

// Desktop only: the "?" in the bottom-right corner. On mobile it's hidden by CSS and the
// FAQ opens from the account menu instead (the bottom bar is full).
export default function FaqButton() {
    const { faq } = useContent();
    const { openFaq } = useFaq();

    return (
        <button
            type="button"
            className={styles.button}
            onClick={openFaq}
            aria-haspopup="dialog"
            aria-label={faq.open}
            title={faq.open}
        >
            <span aria-hidden="true">?</span>
        </button>
    );
}
