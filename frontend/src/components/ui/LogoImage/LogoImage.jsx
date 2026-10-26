// The xikomu pickaxe, in both themes. The logo's ink parts (handle, head, outlines) follow the
// theme the way tokens.css does: dark ink on the light theme, white on the dark one (dark ink
// on the dark background would disappear). An <img> can't take colours from the page's CSS,
// so there are two copies of the logo and the theme shows one of them.
//
// Both are built into the page bundle (?inline) rather than downloaded separately: the logo is
// on every page, and as its own file it left an empty gap (or the alt text) until it arrived.
import logoInk from "../../../assets/logos/xikomu-logo.svg?inline";
import logoWhite from "../../../assets/logos/xikomu-logo-dark.svg?inline";
import styles from "./LogoImage.module.css";

export default function LogoImage({ alt = "", className = "", ...imgProps }) {
    const classes = (theme) => [styles.logo, theme, className].filter(Boolean).join(" ");
    return (
        <>
            <img src={logoInk} alt={alt} className={classes(styles.forLight)} {...imgProps} />
            <img src={logoWhite} alt={alt} className={classes(styles.forDark)} {...imgProps} />
        </>
    );
}
