import Card from "../../../ui/Card/Card";
import LinkedText from "../../../ui/LinkedText/LinkedText";
import LegalLinks from "../LegalLinks/LegalLinks";
import { useContent } from "../../../../hooks/useContent";
import styles from "./LegalDoc.module.css";

// One legal document (content/en/legal.js): a dark header with its name and date, the intro,
// numbered sections of paragraphs and lists, and the row of legal links at the bottom.
export default function LegalDoc({ doc }) {
    const { legal } = useContent();
    const values = { operator: `${legal.operator.name}, ${legal.operator.description}` };
    const text = (value) => <LinkedText text={value} values={values} />;

    return (
        <Card as="article" border={3} shadow={6}>
            <header className={styles.header}>
                <h2 className={styles.heading}>{doc.heading}</h2>
                <p className={styles.updated}>{doc.updated}</p>
            </header>

            <div className={styles.body}>
                {doc.intro.map((paragraph) => (
                    <p key={paragraph} className={styles.intro}>
                        {text(paragraph)}
                    </p>
                ))}

                {doc.sections.map((section) => (
                    <section key={section.h} className={styles.section}>
                        <h3 className={styles.title}>{section.h}</h3>
                        {section.body.map((block, index) =>
                            Array.isArray(block) ? (
                                <ul key={index} className={styles.list}>
                                    {block.map((item) => (
                                        <li key={item}>{text(item)}</li>
                                    ))}
                                </ul>
                            ) : (
                                <p key={index} className={styles.paragraph}>
                                    {text(block)}
                                </p>
                            )
                        )}
                    </section>
                ))}
            </div>

            <footer className={styles.footer}>
                <LegalLinks />
            </footer>
        </Card>
    );
}
