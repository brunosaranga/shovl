import { Link } from "react-router-dom";
import styles from "./Button.module.css";

// One button for everything:
//   <Button to="/dashboard">     → router link
//   <Button href="https://…">    → external link (new tab)
//   <Button onClick={…}>         → <button>
// variant: primary (neon, the "dig deeper" button) | stop (primary-sized, red) | small | danger | dark | quiet
export default function Button({ children, to, href, variant = "primary", type = "button", className = "", ...rest }) {
    const classes = [styles.button, styles[variant], className].filter(Boolean).join(" ");

    if (to) {
        return (
            <Link to={to} className={classes} {...rest}>
                {children}
            </Link>
        );
    }

    if (href) {
        return (
            <a href={href} className={classes} target="_blank" rel="noopener noreferrer" {...rest}>
                {children}
            </a>
        );
    }

    return (
        <button type={type} className={classes} {...rest}>
            {children}
        </button>
    );
}
