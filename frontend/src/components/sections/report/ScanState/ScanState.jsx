import Alert from "../../../ui/Alert/Alert";
import Button from "../../../ui/Button/Button";
import Spinner from "../../../ui/Spinner/Spinner";
import { useContent } from "../../../../hooks/useContent";
import { isInProgress } from "../../../../lib/severity";
import styles from "./ScanState.module.css";

// A report for a scan that isn't complete: still running, paused, failed, interrupted or stopped.
// Failed and stopped scans store why in results.error { reason, message }.
export default function ScanState({ scan, onReRun }) {
    const { report, common } = useContent();
    const state = report.state[scan.status === "pending" ? "running" : scan.status] || report.state.failed;
    const explained = scan.status === "failed" || scan.status === "stopped";
    const message = explained ? scan.results?.error?.message || state.text : state.text;
    const inProgress = isInProgress(scan.status);

    return (
        <Alert
            tone={inProgress ? "info" : "danger"}
            title={state.title}
            actions={inProgress ? null : <Button onClick={onReRun}>{report.rerun}</Button>}
        >
            {inProgress ? (
                <span className={styles.spinner}>
                    <Spinner paused={scan.status === "paused"} />
                </span>
            ) : null}
            <p>{message}</p>
            {inProgress ? null : <p>{common.didNotCount}</p>}
        </Alert>
    );
}
