import { useState, useRef } from 'react'

import PageShell from '../components/layout/PageShell'
import URLInput from '../components/scan/URLInput'
import { PrimaryButton } from '../components/layout/Buttons'
import ToggleRow from '../components/landing/ToggleRow'
import BrandHero from '../components/landing/BrandHero'
import useScan from '../components/scan/HandleScan'
import useWindowSize from '../hooks/useWindowSize'

export default function Landing() {
    const [url, setUrl] = useState('')
    const [verbose, setVerbose] = useState(false)
    const [generateReport, setGenerateReport] = useState(true)
    const [suggestFix, setSuggestFix] = useState(false)
    const [urlError, setUrlError] = useState(false)
    const urlInputRef = useRef(null)
    const { startScan } = useScan()

    const windowWidth = useWindowSize()
    const isMobile = windowWidth <= 768

    const handleScanTrigger = () => {
        startScan({
            url,
            verbose,
            generateReport,
            suggestFix,
            setUrlError,
            urlInputRef
        })
    }

    const urlInput = (
        <URLInput
            ref={urlInputRef}
            url={url}
            setUrl={setUrl}
            onSearchSubmit={handleScanTrigger}
            hasError={urlError}
        />
    )

    return (
        <PageShell
            // Navbar slot: desktop only
            centerElement={isMobile ? null : urlInput}
        >
            <div className='landing'>
                <ToggleRow
                    verbose={verbose} setVerbose={setVerbose}
                    generateReport={generateReport} setGenerateReport={setGenerateReport}
                    suggestFix={suggestFix} setSuggestFix={setSuggestFix}
                />

                {/* Mobile-only: URLInput detached from Navbar, positioned in page body */}
                {isMobile && (
                    <div className='landing-mobile-input'>
                        {urlInput}
                    </div>
                )}

                <BrandHero />

                <div className='primary-action-button-container'>
                    <PrimaryButton onClick={handleScanTrigger}>
                        dig deeper
                    </PrimaryButton>
                </div>
            </div>
        </PageShell>
    )
}