import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import PageBody from "../../components/layout/PageBody/PageBody";
import ProgressBar from "../../components/ui/ProgressBar/ProgressBar";
import Terminal from "../../components/ui/Terminal/Terminal";
import Modal from "../../components/ui/Modal/Modal";
import Button from "../../components/ui/Button/Button";
import ScanHeader from "../../components/sections/scan/ScanHeader/ScanHeader";
import ScanProblem from "../../components/sections/scan/ScanProblem/ScanProblem";
import { useSession } from "../../context/SessionContext";
import { useContent } from "../../hooks/useContent";
import { useLeaveGuard } from "../../hooks/useLeaveGuard";
import { useScanStream } from "../../hooks/useScanStream";

// Runs the scan described in location.state ({ url, verbose, suggest_fix, generate_report })
// and opens the report when it completes.
export default function ScanRunning() {
    const { scan } = useContent();
    const location = useLocation();
    const navigate = useNavigate();
    const { refreshUser } = useSession();

    const options = location.state?.url ? location.state : null;
    const [paused, setPaused] = useState(false);

    const stream = useScanStream({ options, enabled: Boolean(options) });
    const { blocker, allowNextLeave } = useLeaveGuard(stream.isActive);

    // Finished one way or another: the allowance may have changed.
    const done = !stream.isActive;
    useEffect(() => {
        if (done) refreshUser();
    }, [done, refreshUser]);

    useEffect(() => {
        if (stream.phase !== "complete" || !stream.scanId) return undefined;
        const timer = setTimeout(() => navigate(`/scan/${stream.scanId}/report`, { replace: true }), 1500);
        return () => clearTimeout(timer);
    }, [stream.phase, stream.scanId, navigate]);

    if (!options) return <Navigate to="/" replace />;

    const togglePause = () => {
        setPaused((value) => {
            stream.setPaused(!value);
            return !value;
        });
    };

    const stop = () => {
        allowNextLeave();
        stream.stop();
        navigate("/dashboard");
    };

    return (
        <>
            <PageMeta title={scan.meta} />

            <PageBody width="narrow" gap="lg">
                <ScanHeader targetUrl={options.url} active={stream.isActive} paused={paused} onTogglePause={togglePause} onStop={stop} />
                <ProgressBar value={stream.progress} label={scan.title} />

                {stream.problem ? (
                    <ScanProblem problem={stream.problem} options={options} onRetry={stream.restart} />
                ) : null}

                {/* "verbose" is the live-output knob: the terminal only shows when it's on. */}
                {options.verbose ? (
                    <Terminal lines={stream.logs} footer={stream.phase === "complete" ? scan.terminal.complete : null} />
                ) : null}
            </PageBody>

            <Modal
                open={blocker.state === "blocked"}
                title={scan.leave.title}
                onClose={() => blocker.reset?.()}
                actions={
                    <>
                        <Button onClick={() => blocker.reset?.()}>{scan.leave.stay}</Button>
                        <Button variant="stop" onClick={() => blocker.proceed?.()}>
                            {scan.leave.leave}
                        </Button>
                    </>
                }
            >
                <p>{scan.leave.text}</p>
            </Modal>
        </>
    );
}
