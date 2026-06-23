// useScan — decides where the "dig deeper" action sends the user.
//
// Flow:
//   no url           -> shake the input
//   not signed in    -> /signin (scanning needs an account; ToS captured at register)
//   practice target  -> /scan/running directly (httpbin, postman-echo, localhost,
//                       127.0.0.1 need no ownership proof — skip /verify entirely)
//   real domain      -> /verify, carrying the scan options
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { normalizeTargetUrl, isPracticeTarget } from '../../api/targets'

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

        const target = normalizeTargetUrl(url)
        const scanState = {
            url: target,
            verbose: Boolean(verbose),
            suggest_fix: Boolean(suggestFix),
            generate_report: Boolean(generateReport),
        }

        if (!accessToken && !localStorage.getItem('access_token')) {
            navigate('/signin', { state: { pendingScan: scanState } })
            return
        }

        // Practice targets skip ownership verification entirely.
        if (isPracticeTarget(target)) {
            navigate('/scan/running', { state: scanState })
            return
        }

        navigate('/verify', { state: scanState })
    }

    return { startScan }
}