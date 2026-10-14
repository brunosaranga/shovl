import { useContent } from "../../../../hooks/useContent";
import styles from "./VerifyIntro.module.css";

export default function VerifyIntro({ targetUrl }) {
    const { verify } = useContent();
    return (
        <div>
            <h2 className={styles.title}>{verify.title}</h2>
            <p className={styles.target}>
                {verify.target} <strong className={styles.badge}>{targetUrl}</strong>
            </p>
        </div>
    );
}
