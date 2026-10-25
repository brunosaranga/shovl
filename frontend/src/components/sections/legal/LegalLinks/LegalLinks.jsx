import { Fragment } from "react";
import { Link } from "react-router-dom";
import { useContent } from "../../../../hooks/useContent";
import styles from "./LegalLinks.module.css";

const PAGES = ["pricing", "terms", "privacy", "refunds"];

// pricing · terms · privacy · refunds. Paddle asks for the legal pages to be reachable from the
// site's navigation: the row sits on the landing (the desktop footer, and under the launch card
// on phones) and at the bottom of the legal and pricing pages themselves.
//   variant: footer (white, on the ground) | page
export default function LegalLinks({ variant = "page" }) {
    const { legal } = useContent();
    return (
        <nav aria-label={legal.links.label} className={`${styles.links} ${styles[variant]}`}>
            {PAGES.map((page, index) => (
                <Fragment key={page}>
                    {index ? (
                        <span className={styles.separator} aria-hidden="true">
                            ·
                        </span>
                    ) : null}
                    <Link to={`/${page}`} className={styles.link}>
                        {legal.links[page]}
                    </Link>
                </Fragment>
            ))}
        </nav>
    );
}
