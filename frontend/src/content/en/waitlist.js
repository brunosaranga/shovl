// The launch list (backend waitlist/): the modal after a first scan, the tick at sign-up, and
// the pages its emails link to. `consent.version` and `consent.text` must match CONSENT_VERSION
// and CONSENT_TEXT in backend/shovl/waitlist/services.py: change both together. consent.text is
// shown word for word next to the modal's button and as the sign-up tick's label, because it's
// what the backend stores as agreed.
export const waitlist = {
    consent: {
        version: "2026-10-28",
        text: "Email me once when xikomu officially launches. Nothing else, and I can remove myself any time.",
    },

    modal: {
        title: "want to hear when xikomu launches?",
        lead: "xikomu is in beta. leave your name and email and we'll send you one email on launch day.",
        name: "What can we call you?",
        namePlaceholder: "first name",
        email: "Email",
        emailPlaceholder: "you@company.com",
        submit: "email me when it launches",
        busy: "sending...",
        skip: "no thanks",
        close: "close",
        // Shown after sending (the server's own words come first).
        pendingTitle: "check your inbox.",
        confirmedTitle: "you're on the list.",
        privacy: "how we keep it: [privacy policy](/privacy)",
    },

    // /waitlist/confirm and /waitlist/leave (the buttons in the list's emails).
    pages: {
        meta: "launch list | xikomu",
        pageTitle: "launch list",
        confirm: {
            title: "one email when xikomu launches?",
            lead: "press the button to confirm. you'll get one email on launch day, nothing else, and you can remove yourself any time.",
            button: "confirm",
            busy: "confirming...",
            doneTitle: "you're on the list.",
            done: "one email when xikomu launches. every email from the list has a link to remove yourself.",
        },
        leave: {
            title: "leave the launch list?",
            lead: "press the button and your name and address are deleted from the list. you won't get the launch email.",
            button: "remove me",
            busy: "removing...",
            doneTitle: "done.",
            done: "you're off the list, and your name and address are deleted.",
        },
        missing: "this link is missing its code. open it again from the email.",
        home: "go to xikomu",
    },
};
