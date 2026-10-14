import styles from "./Badge.module.css";

// Small coloured label. The colour comes from `tone` (see lib/severity.js):
//   critical | high | medium | low | pass | error | incomplete | accent | neutral | danger
// size: xs (threat chips) | sm (findings, risk) | md (scan status)
// textCase: upper | lower | none
export default function Badge({ tone = "neutral", size = "sm", textCase = "upper", bordered = true, className = "", children }) {
    const classes = [
        styles.badge,
        styles[tone],
        styles[size],
        styles[textCase],
        bordered ? styles.bordered : "",
        className,
    ]
        .filter(Boolean)
        .join(" ");
    return <span className={classes}>{children}</span>;
}
