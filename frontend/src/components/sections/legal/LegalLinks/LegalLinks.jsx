import { Fragment } from "react";
import { Link } from "react-router-dom";
import { useContent } from "../../../../hooks/useContent";
import styles from "./LegalLinks.module.css";

const PAGES = ["pricing", "terms", "privacy", "refunds"];

// pricing · terms · privacy · refunds. Paddle asks for the legal pages to be reachable from the
// site's navigation, so the row sits in the desktop footer, the account menu and at the bottom
// of each of those pages.
//   variant: footer (white on the ground) | page | menu (inside the account menu: a group of
//            menu items, so the menu keeps its keyboard and screen-reader semantics)
//   onNavigate: called when a link is followed (the menu closes itself)
export default function LegalLinks({ variant = "page", onNavigate }) {
    const { legal } = useContent();
    const inMenu = variant === "menu";

    const links = PAGES.map((page, index) => (
        <Fragment key={page}>
            {index ? (
                <span className={styles.separator} aria-hidden="true">
                    ·
                </span>
            ) : null}
            <Link to={`/${page}`} className={styles.link} role={inMenu ? "menuitem" : undefined} onClick={onNavigate}>
                {legal.links[page]}
            </Link>
        </Fragment>
    ));

    if (inMenu) {
        return (
            <div role="group" aria-label={legal.links.label} className={`${styles.links} ${styles.menu}`}>
                {links}
            </div>
        );
    }
    return (
        <nav aria-label={legal.links.label} className={`${styles.links} ${styles[variant]}`}>
            {links}
        </nav>
    );
}
