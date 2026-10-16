import { useContent } from "../../../../hooks/useContent";
import incidentReport from "../../../../assets/images/incident-report-asset.jpg";
import styles from "./AuthIntro.module.css";

// Left column of the sign-in page (desktop only).
// The image is imported so Vite bundles it and hands back its final URL;
// a plain path string is never resolved and would show up as text.
export default function AuthIntro() {
    const { auth } = useContent();
    return (
        <div className={styles.intro}>
            <h1 className={styles.title}>{auth.intro.title}</h1>
            <div className={styles.graphic}>
                <img
                    className={styles.image}
                    src={incidentReport}
                    alt={auth.intro.graphicAlt}
                    decoding="async"
                />
            </div>
        </div>
    );
}