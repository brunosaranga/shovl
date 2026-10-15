import PageMeta from "../../components/layout/PageMeta/PageMeta";
import PageBody from "../../components/layout/PageBody/PageBody";
import Button from "../../components/ui/Button/Button";
import { useContent } from "../../hooks/useContent";
import { useSoundCue } from "../../hooks/useSounds";
import styles from "./NotFound.module.css";

// A dead link inside the app plays the error cue. Opened straight from the address bar it
// stays quiet: browsers allow no sound before the first click.
export default function NotFound() {
    const { notFound } = useContent();
    useSoundCue("error", true);

    return (
        <>
            <PageMeta title={notFound.meta} />
            <PageBody width="narrow" gap="lg">
                <div>
                    <h1 className={styles.title}>{notFound.title}</h1>
                    <p className={styles.text}>{notFound.text}</p>
                </div>
                <div>
                    <Button to="/">{notFound.back}</Button>
                </div>
            </PageBody>
        </>
    );
}
