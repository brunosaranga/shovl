import Alert from "../../../ui/Alert/Alert";
import Button from "../../../ui/Button/Button";
import { useContent } from "../../../../hooks/useContent";
import { fill, formatTime } from "../../../../lib/text";

// Why a scan didn't run or didn't finish, and what to do next.
//   refused → allowance, guest on a real domain, unverified domain…  (nothing was counted)
//   failed  → the scan ran but couldn't produce a result               (not counted)
//   stopped → stopped elsewhere, or paused for too long                 (not counted)
//   error   → the connection dropped                                    (marked interrupted, not counted)
const TITLES = {
    refused: "refusedTitle",
    failed: "failedTitle",
    stopped: "stoppedTitle",
};

export default function ScanProblem({ problem, options, onRetry }) {
    const { scan, common } = useContent();
    const { actions } = scan.problems;

    const title = scan.problems[TITLES[problem.kind] || "connectionTitle"];

    const register = ["registration_required", "guest_limit_reached"].includes(problem.code);
    const needsVerify = problem.code === "domain_not_verified";
    const limited = ["daily_limit_reached", "too_many_attempts"].includes(problem.code);
    const canRetry = problem.kind !== "refused";

    return (
        <Alert
            title={title}
            role="alert"
            actions={
                <>
                    {register ? (
                        <Button to="/signin" state={{ mode: "register", pendingScan: options }}>
                            {actions.register}
                        </Button>
                    ) : null}
                    {needsVerify ? (
                        <Button to="/verify" state={options}>
                            {actions.verify}
                        </Button>
                    ) : null}
                    {canRetry ? <Button onClick={onRetry}>{actions.retry}</Button> : null}
                    {limited || problem.kind !== "refused" ? (
                        <Button to="/dashboard" variant="small">
                            {actions.dashboard}
                        </Button>
                    ) : (
                        <Button to="/" variant="small">
                            {actions.back}
                        </Button>
                    )}
                </>
            }
        >
            <p>{problem.message}</p>
            {limited && problem.retryAfter ? <p>{fill(scan.problems.retryAt, { time: formatTime(problem.retryAfter) })}</p> : null}
            {problem.kind !== "refused" ? <p>{common.didNotCount}</p> : null}
        </Alert>
    );
}
