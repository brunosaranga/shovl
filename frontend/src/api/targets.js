// Mirrors backend domains/verification.py ALLOWED_PRACTICE_TARGETS.
// Practice targets skip domain ownership verification.
const PRACTICE_TARGETS = ['httpbin.org', 'postman-echo.com', 'localhost', '127.0.0.1']

// Pulls a bare hostname out of whatever the user typed. Tolerates input with or
// without a scheme ("api.example.com", "https://api.example.com/v1", etc.).
export function extractHostname(input) {
    if (!input) return ''
    let value = input.trim()
    if (!/^https?:\/\//i.test(value)) value = `https://${value}`
    try {
        return new URL(value).hostname
    } catch {
        return ''
    }
}

// Ensures a target_url has a scheme — the backend's create endpoint requires one.
export function normalizeTargetUrl(input) {
    if (!input) return ''
    const value = input.trim()
    return /^https?:\/\//i.test(value) ? value : `https://${value}`
}

export function isPracticeTarget(input) {
    const hostname = extractHostname(input)
    if (!hostname) return false
    return PRACTICE_TARGETS.some(
        (t) => hostname === t || hostname.endsWith(`.${t}`)
    )
}