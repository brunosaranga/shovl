// The pricing page (pages/Pricing). Keep it in step with the code: the scan allowance in
// scans/limits.py, shovll watch's slots and cadence in accounts/plans.py, and the price with
// the terms (content/en/legal.js, section 6). In notes and `early`: [label](/path) is a link,
// {email} the support address.
export const pricing = {
    meta: "pricing | shovll",
    title: "pricing",
    lead: "start free. go Pro when shovll watch becomes part of how you ship.",
    perMonth: "/ month",
    current: "your plan",

    plans: {
        free: {
            name: "Free",
            price: "$0",
            note: "no card needed",
            features: [
                "5 scans every 24 hours",
                "your own verified domains, plus practice targets",
                "PDF reports and \"since your last scan\"",
                "shovll watch on 1 API: every week during the beta, every month after",
                "alerts in the bell",
            ],
            cta: {
                anonymous: "create a free account",
                guest: "save your scans",
            },
        },
        pro: {
            name: "Pro",
            price: "$19",
            note: "billed monthly, cancel anytime",
            soon: "soon",
            features: [
                "everything in Free",
                "shovll watch on 5 APIs, every week",
                "email alerts when something gets worse (coming soon)",
            ],
            cta: "opening soon",
        },
    },

    early: "want Pro early? email {email}.",

    notes: [
        "Prices are in US dollars. Sales tax or VAT may be added at checkout, depending on where you are.",
        "Payments are handled by Paddle, our merchant of record.",
        "Cancel anytime, and get a full refund within 14 days of a payment: see the [refund policy](/refunds).",
    ],
};
