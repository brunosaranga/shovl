import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import PageBody from "../../components/layout/PageBody/PageBody";
import PageTitle from "../../components/ui/PageTitle/PageTitle";
import Button from "../../components/ui/Button/Button";
import LinkedText from "../../components/ui/LinkedText/LinkedText";
import PlanCard from "../../components/sections/pricing/PlanCard/PlanCard";
import LegalLinks from "../../components/sections/legal/LegalLinks/LegalLinks";
import { useSession } from "../../context/SessionContext";
import { useContent } from "../../hooks/useContent";
import styles from "./Pricing.module.css";

// /pricing: Free and Pro side by side. Pro isn't on sale until billing exists (Paddle): its
// button says "opening soon" and the note under the cards invites an email instead. When
// billing arrives, the Pro button starts the checkout and "your plan" follows effective_plan.
export default function Pricing() {
    const { pricing } = useContent();
    const { status, user } = useSession();
    const { free, pro } = pricing.plans;
    const plan = status === "registered" ? user?.plan?.name : null;

    const current = <span className={styles.current}>{pricing.current}</span>;

    let freeAction = null;
    if (status === "anonymous" || status === "guest") {
        freeAction = (
            <Button to="/signin" state={{ mode: "register" }} className={styles.cta}>
                {status === "guest" ? free.cta.guest : free.cta.anonymous}
            </Button>
        );
    } else if (plan === "free") {
        freeAction = current;
    }

    const proAction =
        plan === "pro" ? (
            current
        ) : (
            <Button disabled className={styles.cta}>
                {pro.cta}
            </Button>
        );

    return (
        <>
            <PageMeta title={pricing.meta} />
            <NavCenter>
                <PageTitle>{pricing.title}</PageTitle>
            </NavCenter>

            <PageBody width="wide" gap="md">
                <p className={styles.lead}>{pricing.lead}</p>

                <div className={styles.plans}>
                    <PlanCard plan={free} perMonth={pricing.perMonth} action={freeAction} />
                    <PlanCard plan={pro} perMonth={pricing.perMonth} featured badge={pro.soon} action={proAction} />
                </div>

                <div className={styles.notes}>
                    <p className={styles.early}>
                        <LinkedText text={pricing.early} />
                    </p>
                    <ul className={styles.noteList}>
                        {pricing.notes.map((note) => (
                            <li key={note}>
                                <LinkedText text={note} />
                            </li>
                        ))}
                    </ul>
                    <div className={styles.links}>
                        <LegalLinks />
                    </div>
                </div>
            </PageBody>
        </>
    );
}
