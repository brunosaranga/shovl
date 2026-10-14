import styles from "./PageTitle.module.css";

// The page name shown in the navbar's middle slot (pages render it inside <NavCenter>).
export default function PageTitle({ children }) {
    return <h1 className={styles.title}>{children}</h1>;
}
