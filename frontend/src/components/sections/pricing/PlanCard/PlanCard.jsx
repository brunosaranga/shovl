import styles from "./PlanCard.module.css";

// One plan on the pricing page: name, price, a short note, what's included, and the button
// (or "your plan"). `featured` gives Pro the neon edge; `badge` marks it "soon" until billing
// opens.
export default function PlanCard({ plan, perMonth, featured = false, badge = null, action }) {
    return (
        <article className={styles.card} data-featured={featured || undefined}>
            <header className={styles.header}>
                <h2 className={styles.name}>{plan.name}</h2>
                {badge ? <span className={styles.badge}>{badge}</span> : null}
            </header>

            <div className={styles.priceRow}>
                <span className={styles.price}>{plan.price}</span>
                <span className={styles.period}>{perMonth}</span>
            </div>
            <p className={styles.note}>{plan.note}</p>

            <ul className={styles.features}>
                {plan.features.map((feature) => (
                    <li key={feature}>{feature}</li>
                ))}
            </ul>

            <div className={styles.action}>{action}</div>
        </article>
    );
}
