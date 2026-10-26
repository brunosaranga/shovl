// The pricing page (pages/Pricing). Keep it in step with the code: the scan allowance in
// scans/limits.py, murindzi's slots and cadence in accounts/plans.py, and the price with
// the terms (content/en/legal.js, section 6). In notes and `early`: [label](/path) is a link,
// {email} the support address.
export const pricing = {
    meta: "pricing | xikomu",
    // Search results and link previews (scripts/seo-pages.mjs). Keep it in step with the plans.
    description:
        "Start free: 5 scans a day, PDF reports and scheduled re-scans of one API with murindzi. Pro, opening soon at $19 a month, watches 5 APIs every week.",
    title: "pricing",
    lead: "start free. go Pro when murindzi becomes part of how you ship.",
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
                "murindzi re-scans 1 API: every week during the beta, every month after",
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
                "murindzi re-scans 5 APIs, every week",
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
