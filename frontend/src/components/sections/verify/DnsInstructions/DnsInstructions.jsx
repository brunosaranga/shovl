import Card from "../../../ui/Card/Card";
import CopyField from "../../../ui/CopyField/CopyField";
import { useContent } from "../../../../hooks/useContent";
import styles from "./DnsInstructions.module.css";

// The TXT record the backend looks for (domains/verification.py):
//   host:  _shovll-verify.<hostname>    value: <verification_token>
export default function DnsInstructions({ recordName, token }) {
    const { verify } = useContent();

    return (
        <Card border={4} shadow={8} className={styles.card}>
            <div className={styles.step}>{verify.step}</div>

            <div className={styles.row}>
                <span className={styles.label}>{verify.labels.host}</span>
                <code className={styles.value}>{recordName}</code>
            </div>

            <div className={styles.row}>
                <span className={styles.label}>{verify.labels.type}</span>
                <code className={styles.value}>TXT</code>
            </div>

            <div className={styles.row}>
                <span className={styles.label}>{verify.labels.value}</span>
                <CopyField value={token} copyLabel={verify.copy.idle} copiedLabel={verify.copy.done} />
            </div>

            <div className={styles.note}>{verify.propagation}</div>
        </Card>
    );
}
