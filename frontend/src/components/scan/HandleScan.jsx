// rename file to useScan.js
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function useScan() {
    const { accessToken } = useAuth()
    const navigate = useNavigate()

    const startScan = ({ url, verbose, generateReport, suggestFix, setUrlError, urlInputRef }) => {
        if (!url) {
            setUrlError(true)
            urlInputRef.current?.focus()
            setTimeout(() => setUrlError(false), 1500)
            return
        }
        if (!accessToken) {
            navigate('/verify', { state: { pendingScan: { url, verbose, generateReport, suggestFix } } })
            return
        }
        navigate('/scan/new', { state: { url, verbose, generateReport, suggestFix } })
    }

    return { startScan }
}