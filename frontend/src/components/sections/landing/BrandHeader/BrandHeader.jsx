import Logo from "../../../ui/Logo/Logo";
import { useContent } from "../../../../hooks/useContent";
import styles from "./BrandHeader.module.css";

// Mobile-only header: "xikomu" lockup + tagline.
export default function BrandHeader() {
    const { common } = useContent();
    return (
        <div className={styles.header}>
            <Logo variant="lockup" />
            <p className={styles.tagline}>{common.tagline}</p>
        </div>
    );
}
