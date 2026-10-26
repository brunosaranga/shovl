import pickaxeGraphic from "../../../../assets/logos/xikomu-graphic.svg";
import pickaxeGraphicDark from "../../../../assets/logos/xikomu-graphic-dark.svg";
import { useContent } from "../../../../hooks/useContent";
import styles from "./BrandHero.module.css";

// The big pickaxe and "xikomu" wordmark behind the dig-deeper button (desktop only).
// Like the logo (ui/LogoImage), the pickaxe's ink parts follow the theme: dark ink on the
// light theme, white on the dark one, so there are two copies and the theme shows one.
export default function BrandHero() {
    const { common } = useContent();
    return (
        <div className={styles.hero} aria-hidden="true">
            <div className={styles.graphic}>
                <img className={`${styles.pickaxe} ${styles.forLight}`} src={pickaxeGraphic} alt="" />
                <img className={`${styles.pickaxe} ${styles.forDark}`} src={pickaxeGraphicDark} alt="" />
            </div>
            <div className={styles.wordmarkWrap}>
                <p className={styles.wordmark}>{common.brand}</p>
            </div>
        </div>
    );
}
