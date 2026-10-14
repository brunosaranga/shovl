import { useContent } from "../../../../hooks/useContent";
import styles from "./AuthIntro.module.css";

// Left column of the sign-in page (desktop only).
export default function AuthIntro() {
    const { auth } = useContent();
    return (
        <div className={styles.intro}>
            <h1 className={styles.title}>{auth.intro.title}</h1>
            {/* Placeholder until the incident-report illustration exists. */}
            <div className={styles.graphic}>
                <span className={styles.placeholder}>{auth.intro.graphic}</span>
            </div>
        </div>
    );
}
