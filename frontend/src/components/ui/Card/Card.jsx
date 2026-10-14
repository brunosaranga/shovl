import styles from "./Card.module.css";

// The neo-brutalist box: solid border and a hard offset shadow.
//   border: 2 | 3 | 4     shadow: 4 | 5 | 6 | 8
export default function Card({ as: Tag = "div", border = 3, shadow = 6, className = "", children, ...rest }) {
    const classes = [styles.card, styles[`border${border}`], styles[`shadow${shadow}`], className]
        .filter(Boolean)
        .join(" ");
    return (
        <Tag className={classes} {...rest}>
            {children}
        </Tag>
    );
}
