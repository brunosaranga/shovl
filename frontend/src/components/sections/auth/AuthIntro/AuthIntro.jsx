import { useContent } from "../../../../hooks/useContent";
import incidentReport from "../../../../assets/images/incident-report-asset.jpg";
import styles from "./AuthIntro.module.css";

// Left column of the sign-in page (desktop only).
// The image is imported so Vite bundles it and hands back its final URL;
// a plain path string is never resolved and would show up as text.
// It's 2 MB, so it loads after the ground (low priority) and not at all on mobile, where the
// column is hidden (lazy images that aren't displayed are never fetched).
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
                    loading="lazy"
                    fetchPriority="low"
                />
            </div>
        </div>
    );
}