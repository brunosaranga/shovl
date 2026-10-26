import LogoImage from "../LogoImage/LogoImage";
import { useContent } from "../../../hooks/useContent";
import styles from "./Logo.module.css";

// variant:
//   mark    → just the pickaxe (navbar; inverseOnMobile there, since the phone bar is inverse)
//   lockup  → "xikomu" wordmark + pickaxe (auth page, mobile landing header)
// The pickaxe itself, in the right colours for the theme, is ui/LogoImage.
export default function Logo({ variant = "mark", as: Heading = "h1", inverseOnMobile = false }) {
    const { common } = useContent();

    if (variant === "lockup") {
        return (
            <div className={styles.lockup}>
                <Heading className={styles.wordmark}>{common.brand}</Heading>
                <LogoImage className={styles.lockupMark} width="41" height="41" />
            </div>
        );
    }

    return (
        <LogoImage
            className={styles.mark}
            alt={common.logoAlt}
            width="40"
            height="40"
            inverseOnMobile={inverseOnMobile}
        />
    );
}
