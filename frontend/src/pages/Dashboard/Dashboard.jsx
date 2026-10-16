import { useEffect } from "react";
import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import PageBody from "../../components/layout/PageBody/PageBody";
import PageTitle from "../../components/ui/PageTitle/PageTitle";
import ScanStats from "../../components/sections/dashboard/ScanStats/ScanStats";
import GuestNotice from "../../components/sections/dashboard/GuestNotice/GuestNotice";
import ScanList from "../../components/sections/dashboard/ScanList/ScanList";
import { useSession } from "../../context/SessionContext";
import { useContent } from "../../hooks/useContent";
import { useScanList } from "../../hooks/useScans";
import { useSoundCue } from "../../hooks/useSounds";
import { isInProgress } from "../../lib/severity";

export default function Dashboard() {
    const { dashboard } = useContent();
    const { allowance, isGuest, refreshUser } = useSession();
    const { scans, loading, error } = useScanList();
    useSoundCue("error", error);

    // Scans left changes after every scan: show the current number on arrival, and again
    // whenever a scan in progress ends (an interrupted or stopped scan frees its place).
    const inProgress = scans.filter((scan) => isInProgress(scan.status)).length;
    useEffect(() => {
        refreshUser();
    }, [refreshUser, inProgress]);

    return (
        <>
            <PageMeta title={dashboard.meta} />
            <NavCenter>
                <PageTitle>{dashboard.pageTitle}</PageTitle>
            </NavCenter>

            <PageBody width="wide" gap="md" mono>
                <ScanStats scans={scans} allowance={allowance} isGuest={isGuest} />
                {isGuest ? <GuestNotice /> : null}
                <ScanList scans={scans} loading={loading} error={error} />
            </PageBody>
        </>
    );
}
