import { useState } from 'react'

import PageTitle from '../components/common/PageTitle'
import PageShell from '../components/layout/PageShell'
import ScanList from '../components/dashboard/ScanList.jsx'
import ScanStats from '../components/dashboard/ScansStats.jsx'
import Pagination from '../components/layout/Pagination.jsx'


export default function Dashboard() {
    const [expandedScanId, setExpandedScanId] = useState(null)
    const [scanProgress, setScanProgress] = useState(60) // <--- Added missing state definition


    return (
        <PageShell
        centerElement={<PageTitle>dashboard</PageTitle>}>
            <div className='dashboard'>
                
                {/* Scan stats */}
                <ScanStats />


                {/* Scan Items / Queue */}
                <ScanList
                    scanProgress={scanProgress} 
                    setScanProgress={setScanProgress} 
                    expandedScanId={expandedScanId}
                    setExpandedScanId={setExpandedScanId}
                />


                {/* Pagination */}
                <Pagination />

            </div>
        </PageShell>
    )
}