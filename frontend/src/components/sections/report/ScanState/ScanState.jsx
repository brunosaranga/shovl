import Alert from "../../../ui/Alert/Alert";
import Button from "../../../ui/Button/Button";
import Spinner from "../../../ui/Spinner/Spinner";
import { useContent } from "../../../../hooks/useContent";
import styles from "./ScanState.module.css";

// A report for a scan that isn't complete: still running, failed or interrupted.
// A failed scan stores why in results.error { reason, message }.
export default function ScanState({ scan, onReRun }) {
    const { report, common } = useContent();
    const state = report.state[scan.status === "pending" ? "running" : scan.status] || report.state.failed;
    const message = scan.status === "failed" ? scan.results?.error?.message || state.text : state.text;
    const running = scan.status === "running" || scan.status === "pending";

    return (
        <Alert
            tone={running ? "info" : "danger"}
            title={state.title}
            actions={running ? null : <Button onClick={onReRun}>{report.rerun}</Button>}
        >
            {running ? (
                <span className={styles.spinner}>
                    <Spinner />
                </span>
            ) : null}
            <p>{message}</p>
            {running ? null : <p>{common.didNotCount}</p>}
        </Alert>
    );
}
