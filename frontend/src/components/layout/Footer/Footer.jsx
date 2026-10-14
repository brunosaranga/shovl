import { useContent } from "../../../hooks/useContent";
import styles from "./Footer.module.css";

export default function Footer() {
    const { common } = useContent();
    return <footer className={styles.footer}>{common.footer}</footer>;
}
