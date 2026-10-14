export const landing = {
    meta: "shovl | break your API before someone else does",

    url: {
        label: "URL:",
        placeholder: "paste your API URL...",
        placeholderEmpty: "enter a URL first",
        ariaLabel: "API URL to scan",
    },

    options: {
        verbose: "verbose",
        generateReport: "generate report",
        suggestFix: "suggest fix",
    },

    cta: "dig deeper",
    starting: "starting...",

    // Shown next to the button when nobody is signed in: ticking it creates the guest session.
    consent: "I own or have explicit permission to test this URL",
    consentRequired: "tick the box first: only scan APIs you're allowed to test.",
    invalidUrl: "that doesn't look like a URL. try something like api.example.com",

    allowance: {
        anonymous: "3 free practice scans. no sign-up.",
        guest: "{remaining} of {limit} free scans left",
        registered: "{remaining} of {limit} scans left today",
    },

    createAccount: "create a free account",

    // One-click practice targets under the button (anyone who isn't registered).
    tryLabel: "try:",
    tryAria: "put {url} in the URL box",
};
