// Whether this browser has already been asked to join the launch list (the modal after a first
// scan, or the tick at sign-up). Asked once, never again. Storage can be unavailable (private
// mode, blocked site data): then it's remembered for the visit only.
const KEY = "shovl.waitlist";
let seenThisVisit = false;

export function waitlistSeen() {
    if (seenThisVisit) return true;
    try {
        return localStorage.getItem(KEY) !== null;
    } catch {
        return false;
    }
}

export function markWaitlistSeen() {
    seenThisVisit = true;
    try {
        localStorage.setItem(KEY, "asked");
    } catch {
        // storage unavailable: remembered for this visit only
    }
}
