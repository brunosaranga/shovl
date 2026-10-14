import shovelGraphic from "../../../../assets/logos/ShovelGraphic.svg";
import { useContent } from "../../../../hooks/useContent";
import styles from "./BrandHero.module.css";

// The big shovel and "shovl" wordmark behind the dig-deeper button (desktop only).
export default function BrandHero() {
    const { common } = useContent();
    return (
        <div className={styles.hero} aria-hidden="true">
            <div className={styles.graphic}>
                <img className={styles.shovel} src={shovelGraphic} alt="" />
            </div>
            <div className={styles.wordmarkWrap}>
                <p className={styles.wordmark}>{common.brand}</p>
            </div>
        </div>
    );
}
