// The page the "turn these emails off" link in murindzi's emails opens (pages/EmailOff).
// Nothing happens until the button is pressed: some mail scanners open every link.
export const emailOff = {
    meta: "turn off murindzi's emails | xikomu",
    pageTitle: "emails",

    title: "turn off murindzi's emails?",
    lead: "murindzi emails you when a watched API gets worse, or when it has to pause a watch. turning the emails off doesn't stop murindzi: it keeps scanning, and what it finds still lands in the bell.",
    button: {
        idle: "turn them off",
        busy: "turning off...",
    },

    doneTitle: "done.",
    done: "murindzi won't email you any more. you can turn the emails back on in settings, under murindzi.",
    missing: "this link is missing its code. open it again from the email, or turn the emails off in settings.",
    settings: "open settings",
};
