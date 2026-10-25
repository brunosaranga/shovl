import { Fragment } from "react";
import { Link } from "react-router-dom";
import { useContent } from "../../../hooks/useContent";
import styles from "./LinkedText.module.css";

// [label](href), {key}
const TOKEN = /\[([^\]]+)\]\(([^)\s]+)\)|\{(\w+)\}/g;

// Copy from content/ with links in it:
//   "[label](/path)"  a link inside the site ("[label](https://…)" opens in a new tab)
//   "{email}"         the support address, as a mailto link
//   "{securityEmail}" the security address, as a mailto link
//   "{key}"           any other value from `values`
// newTab: open site links in a new tab too, for links inside a form (the consent ticks), so a
// half-filled form isn't lost.
export default function LinkedText({ text, values = {}, newTab = false }) {
    const { common } = useContent();
    const parts = [];
    let last = 0;
    let index = 0;

    for (const match of String(text ?? "").matchAll(TOKEN)) {
        if (match.index > last) parts.push(text.slice(last, match.index));
        const [whole, label, href, key] = match;
        const id = index++;
        if (label) {
            const external = /^https?:\/\//.test(href);
            parts.push(
                external || newTab ? (
                    <a key={id} href={href} className={styles.link} target="_blank" rel="noopener noreferrer">
                        {label}
                    </a>
                ) : (
                    <Link key={id} to={href} className={styles.link}>
                        {label}
                    </Link>
                )
            );
        } else if (key === "email" || key === "securityEmail") {
            const address = key === "email" ? common.contactEmail : common.securityEmail;
            parts.push(
                <a key={id} href={`mailto:${address}`} className={styles.link}>
                    {address}
                </a>
            );
        } else {
            parts.push(values[key] ?? whole);
        }
        last = match.index + whole.length;
    }
    if (last < String(text ?? "").length) parts.push(text.slice(last));

    return parts.map((part, i) => <Fragment key={i}>{part}</Fragment>);
}
