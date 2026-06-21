import { useState } from 'react'
import PageShell from '../components/layout/PageShell'
import PageTitle from '../components/common/PageTitle'
import ReportMetaCard from '../components/report/ReportMetaCard'
import SeverityMatrix from '../components/report/SeverityMatrix'
import FindingsList from '../components/report/FindingsList'

export default function Report() {
    // 0 - closed
    // 1 - open
    const [openFindingId, setOpenFindingId] = useState(0)

    return (
        <PageShell centerElement={<PageTitle>report</PageTitle>}>
            <div className="report-container">
                <ReportMetaCard />
                <SeverityMatrix />
                <FindingsList
                    openFindingId={openFindingId}
                    setOpenFindingId={setOpenFindingId}
                />
            </div>
        </PageShell>
    )
}