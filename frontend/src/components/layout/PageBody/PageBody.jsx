import styles from "./PageBody.module.css";

// The centred column every page's content sits in.
//   width: wide (960px: dashboard, report, settings) | narrow (800px: scan running, verify)
//   gap:   md (32px) | lg (40px)
//   top:   page (clears the navbar) | compact (verify page)
//   mono:  set the page's base font to the mono face
export default function PageBody({ width = "wide", gap = "md", top = "page", mono = false, className = "", children }) {
    const classes = [styles.body, styles[width], styles[`gap-${gap}`], styles[`top-${top}`], mono ? styles.mono : "", className]
        .filter(Boolean)
        .join(" ");
    return <div className={classes}>{children}</div>;
}
