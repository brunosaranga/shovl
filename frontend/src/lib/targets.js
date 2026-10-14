// Mirrors ALLOWED_PRACTICE_TARGETS in backend domains/verification.py.
// Practice targets skip domain ownership verification.
const PRACTICE_TARGETS = ["postman-echo.com"];

// Mirrors LOCAL_PRACTICE_TARGETS in the backend. Development builds only: in
// production these would point at our own server, so they are not practice targets.
const LOCAL_PRACTICE_TARGETS = ["localhost", "127.0.0.1"];

const ACTIVE_PRACTICE_TARGETS = import.meta.env.DEV
    ? [...PRACTICE_TARGETS, ...LOCAL_PRACTICE_TARGETS]
    : PRACTICE_TARGETS;

// Pulls a bare hostname out of whatever the user typed. Tolerates input with or
// without a scheme ("api.example.com", "https://api.example.com/v1", etc.).
export function extractHostname(input) {
    if (!input) return "";
    let value = input.trim();
    if (!/^https?:\/\//i.test(value)) value = `https://${value}`;
    try {
        return new URL(value).hostname;
    } catch {
        return "";
    }
}

// Ensures a target_url has a scheme: the backend requires one.
export function normalizeTargetUrl(input) {
    if (!input) return "";
    const value = input.trim();
    return /^https?:\/\//i.test(value) ? value : `https://${value}`;
}

export function isPracticeTarget(input) {
    const hostname = extractHostname(input);
    if (!hostname) return false;
    return ACTIVE_PRACTICE_TARGETS.some((target) => hostname === target || hostname.endsWith(`.${target}`));
}
