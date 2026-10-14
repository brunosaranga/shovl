import styles from "./Pagination.module.css";

// Page buttons. Renders nothing when everything fits on one page.
export default function Pagination({ page, pageCount, onChange, label = "page" }) {
    if (pageCount <= 1) return null;
    return (
        <nav className={styles.pagination} aria-label={label}>
            {Array.from({ length: pageCount }, (_, index) => index + 1).map((number) => (
                <button
                    key={number}
                    type="button"
                    className={number === page ? `${styles.page} ${styles.active}` : styles.page}
                    aria-current={number === page ? "page" : undefined}
                    onClick={() => onChange(number)}
                >
                    {number}
                </button>
            ))}
        </nav>
    );
}
