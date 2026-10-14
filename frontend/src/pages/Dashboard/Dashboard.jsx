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

export default function Dashboard() {
    const { dashboard } = useContent();
    const { allowance, isGuest, refreshUser } = useSession();
    const { scans, loading, error } = useScanList();

    // Scans left changes after every scan: always show the current number here.
    useEffect(() => {
        refreshUser();
    }, [refreshUser]);

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
