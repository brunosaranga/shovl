import PageMeta from "../../components/layout/PageMeta/PageMeta";
import PageBody from "../../components/layout/PageBody/PageBody";
import Button from "../../components/ui/Button/Button";
import { useContent } from "../../hooks/useContent";
import styles from "./NotFound.module.css";

export default function NotFound() {
    const { notFound } = useContent();
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
