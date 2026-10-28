// The terms, the privacy policy and the refund policy (pages/Legal), and the row of links to
// them and the pricing page (footer, account menu, the bottom of each document).
//
// Written for xikomu as it works today. Not legal advice: have them checked before relying on
// them, and keep them in step with the code: scan limits in scans/limits.py, the 30-day guest
// clean-up in accounts/management/commands/purge_guests.py, murindzi's cadence in
// accounts/plans.py, hosting in the deployment notes.
//
// In the text: [label](/path) becomes a link, {email} the support address (common.contactEmail),
// {securityEmail} the security address (common.securityEmail), {operator} who runs xikomu
// (below). A string in `body` is a paragraph, an array is a list.

// Who runs xikomu. When you register, change it to match the registration: your full legal name
// as registered, "a sole trader registered in Mozambique", the registration number and NUIT,
// and the address you register with.
export const operator = {
    name: "Bruno Saranga",
    description: "an individual based in Maputo, Mozambique",
};

const UPDATED = "last updated: 28 October 2026";

export const legal = {
    operator,

    links: {
        label: "legal",
        pricing: "pricing",
        terms: "terms",
        privacy: "privacy",
        refunds: "refunds",
    },

    terms: {
        meta: "terms | xikomu",
        // Search results and link previews (scripts/seo-pages.mjs)
        description:
            "The terms of service for xikomu, the API security scanner: what you may scan, accounts, plans and payments, and liability.",
        title: "terms",
        heading: "terms of service",
        updated: UPDATED,
        intro: [
            "These terms are the agreement between you and {operator} (\"xikomu\", \"we\", \"us\") for using xikomu, on this website and through its API. By creating a guest session, registering or using xikomu, you agree to them. If you don't agree, please don't use xikomu.",
            "xikomu is in beta: things will change, and some things will break. These terms describe what xikomu does today.",
        ],
        sections: [
            {
                h: "1. what xikomu does",
                body: [
                    "xikomu runs six automated checks against an API address you give it (authentication, object-level access, mass assignment, rate limiting, misconfiguration and data exposure) and shows you a report. With murindzi, it re-runs those checks on a schedule for your own verified APIs and tells you when something gets worse.",
                    "xikomu is a tool, not a penetration test, an audit or a guarantee. Automated checks miss things, and sometimes flag things that are fine. A clean report doesn't mean your API is secure, and the decisions you make based on a report are yours.",
                ],
            },
            {
                h: "2. only scan what you're allowed to",
                body: [
                    "You may only scan APIs that you own, or that you have the owner's explicit permission to test. This is the most important rule in these terms.",
                    [
                        "Guests can scan the public practice targets listed on the site, and nothing else.",
                        "To scan your own domain, you need a registered account and must prove you control the domain (with a DNS record or a file). Keep that record in place: xikomu checks it again before every scheduled scan.",
                        "A scan sends real requests from our servers to the address you choose, including a short burst of up to 15 quick requests to test rate limiting. On your own domains xikomu only reads: the one check that sends data runs on practice targets only.",
                        "You're responsible for making sure a scan is allowed, including by the rules of your hosting provider and of anyone else whose systems the address reaches.",
                    ],
                    "If someone makes a claim against us because you scanned something you weren't allowed to, you agree to cover our reasonable costs of dealing with it, as far as the law allows.",
                ],
            },
            {
                h: "3. acceptable use",
                body: [
                    "Don't:",
                    [
                        "scan, probe or attack systems you're not allowed to test, or use xikomu's results to harm anyone;",
                        "get around domain verification, scan limits or any other safeguard, including by calling the API directly;",
                        "overload xikomu, interfere with how it works, or create accounts automatically;",
                        "use xikomu to break any law, or resell it without our written permission.",
                    ],
                    "We may suspend or close an account that breaks these terms or puts xikomu or other people at risk. Where it's reasonable, we'll tell you first and give you a chance to explain.",
                ],
            },
            {
                h: "4. accounts",
                body: [
                    "Use a real email address, keep your password to yourself, and tell us at {email} if you think someone else has used your account. You're responsible for what happens under it.",
                    "Confirm your email address with the 6-digit code we send you. Until then the account can't scan your own domains or use murindzi, and an account that isn't confirmed within 7 days of signing up is deleted, with its scans.",
                    "A guest session is an account without an email address. It's deleted with its scans 30 days after it was created, unless you register or sign in from it first.",
                    "You can ask us to delete your account at any time by emailing {email} from the address you signed up with. That deletes your scans, domains and watched APIs too (see the [privacy policy](/privacy)).",
                ],
            },
            {
                h: "5. plans",
                body: [
                    "The free plan includes a set number of scans and one watched API, as shown on the [pricing page](/pricing). Its limits can change, especially during the beta: for example, murindzi re-scans the free plan's API every week during the beta and every month after it.",
                    "Pro is a paid monthly subscription. It isn't on sale yet; when it opens, section 6 applies to it.",
                ],
            },
            {
                h: "6. payments",
                body: [
                    "Our order process is conducted by our online reseller Paddle.com. Paddle.com is the Merchant of Record for all our orders. Paddle provides all customer service inquiries and handles returns. When you buy Pro, you buy it from Paddle under Paddle's buyer terms, which also cover payment, invoices and taxes.",
                    [
                        "Pro costs USD 19 a month. Sales tax or VAT may be added at checkout, depending on where you are.",
                        "It renews every month until you cancel. You can cancel at any time, and Pro stays active until the end of the month you've paid for.",
                        "If a renewal payment can't be collected, Pro features may stop until it's paid. Your data stays.",
                        "If the price changes, we'll tell you by email at least 30 days before, and the new price applies from your next renewal after that.",
                        "Refunds follow the [refund policy](/refunds).",
                    ],
                ],
            },
            {
                h: "7. your data and ours",
                body: [
                    "Your account details, domains and scan results are yours. You allow us to store and process them to run xikomu, as the [privacy policy](/privacy) explains.",
                    "xikomu's software, design and name are ours. If you send us feedback or ideas, we may use them without owing you anything.",
                ],
            },
            {
                h: "8. availability",
                body: [
                    "We try to keep xikomu running, but we don't promise it will always be available, fast or free of errors, especially during the beta. We may change, pause or stop features, and we'll give notice of big changes where we can.",
                ],
            },
            {
                h: "9. liability",
                body: [
                    "xikomu is provided \"as is\". As far as the law allows:",
                    [
                        "we're not liable for indirect or consequential losses, such as lost profits, lost data or business interruption;",
                        "our total liability for any claim connected with xikomu is limited to what you paid us in the 12 months before the claim, or USD 50 if you haven't paid anything.",
                    ],
                    "Nothing in these terms limits liability that the law doesn't allow to be limited, such as for fraud, or for death or personal injury caused by negligence. If you're a consumer, you keep the rights consumer law gives you.",
                ],
            },
            {
                h: "10. changes to these terms",
                body: [
                    "We may update these terms. If a change matters, we'll tell registered users, on the site or by email, at least 14 days before it applies. If you keep using xikomu after that, the new terms apply; if you don't agree with them, you can close your account.",
                ],
            },
            {
                h: "11. law and disputes",
                body: [
                    "These terms are governed by the laws of the Republic of Mozambique, and disputes go to the courts of Maputo. If you're a consumer, you also keep the protection of the mandatory laws of the country where you live, and you may be able to bring a claim in your local courts.",
                    "Before going to court, please write to us at {email}: most problems are quicker to fix by talking.",
                ],
            },
            {
                h: "12. contact",
                body: ["xikomu (called shovll until 26 October 2026) is run by {operator}. Email: {email}."],
            },
        ],
    },

    privacy: {
        meta: "privacy | xikomu",
        description:
            "What personal data xikomu keeps, why, who else handles it, and how to see, correct or delete yours.",
        title: "privacy",
        heading: "privacy policy",
        updated: UPDATED,
        intro: [
            "This page explains what personal data xikomu keeps, why, who else handles it, and what you can ask us to do with it. xikomu is run by {operator}, who is responsible for your data (the \"controller\"). Questions go to {email}.",
            "The short version: we keep what's needed to run your account and your scans. Nothing is sold, there are no ads, no analytics and no tracking, and your data is stored in Frankfurt, Germany.",
        ],
        sections: [
            {
                h: "what we keep, and why",
                body: [
                    [
                        "Your account: your email address, your password (only as a one-way hash, which can't be read back), when you accepted the terms, your plan and your settings. To run your account.",
                        "Email codes: the 6-digit codes we email you to confirm your address or reset your password, only as a one-way hash. To make sure the address is yours. Deleted once used or replaced, and within a day once expired. An account that signs up and isn't confirmed within 7 days is deleted, with its scans.",
                        "Guest sessions: an account without an email address, and its scans. To let you try xikomu without signing up. Deleted 30 days after it was created.",
                        "Your domains: the hostnames you add, their verification codes and whether they're verified. To make sure you only scan what you control.",
                        "Your scans: the addresses you scan, the options you chose and the results. With \"verbose\" on, results include the raw responses your API sent back, so they contain whatever your API returned. For your reports, \"since your last scan\" and PDF downloads (built when you ask, never stored).",
                        "murindzi: the APIs being watched, their schedule, the notifications in your bell, and whether you want them by email. To run scheduled scans and tell you what they found: in the bell, and by email unless you turn that off or mute the bell.",
                        "Report feedback: your answers and comment under a report, with a copy of the report's summary. To improve xikomu. If the scan is deleted, the answer stays, without your account or the scanned address.",
                        "Network addresses: when a guest session or an account is created, or a password reset is asked for, your IP address is counted for up to an hour, to limit how many one network can make. Our hosting provider also keeps short-lived server logs (IP address, time, request) for security and fixing errors.",
                        "Emails we send you: a record of each one (what kind, when, and whether it went out), with your address only as a one-way hash. To stay within our sending limits and find delivery problems. Deleted after 90 days.",
                        "Emails you send us: your address and your message, to reply.",
                    ],
                ],
            },
            {
                h: "the legal basis",
                body: [
                    "We use your data to provide the service you signed up for (a contract with you), and for our legitimate interests in keeping xikomu secure, preventing abuse and improving it. Once payments exist, we'll also keep payment records because tax law requires it. Nothing here relies on consent, and we don't send marketing emails.",
                ],
            },
            {
                h: "in your browser",
                body: [
                    "xikomu keeps a few things in your browser's local storage: your session, your theme and sound settings, and whether you skipped a feedback question. They're needed for the site to work. xikomu doesn't use tracking cookies, analytics or ads, and its fonts are served by xikomu itself, so visiting sends nothing to anyone else.",
                ],
            },
            {
                h: "who else handles it",
                body: [
                    "A few providers process data for us, only to run xikomu:",
                    [
                        "Render hosts the site and the API, in Frankfurt, Germany.",
                        "Neon hosts the database, in Frankfurt, Germany.",
                        "GitHub runs the daily job that deletes expired guest sessions and accounts that were never confirmed.",
                        "Cloudflare forwards the emails you send to our xikomu.com addresses, like {email}, to Gmail (Google), where they're read and answered.",
                        "Brevo, in France, delivers the emails we send from our xikomu.com addresses. It counts how many are opened and which links are clicked, without recording who opened or clicked them.",
                        "Paddle, once Pro is on sale, handles payments as the merchant of record. Paddle collects your payment details itself; we receive your name, email, country and subscription status, never your card number.",
                    ],
                    "When you run a scan, our servers send the requests to the address you chose, so the scanned API sees our servers, not you.",
                    "We never sell your data or share it with advertisers. We'd only disclose it if the law required us to.",
                ],
            },
            {
                h: "where it's stored",
                body: [
                    "Your data is stored in Frankfurt, Germany. xikomu is run from Mozambique, and our providers may access data from other countries (the United States, for example) under their own safeguards, such as the European Commission's standard contractual clauses.",
                ],
            },
            {
                h: "how long we keep it",
                body: [
                    [
                        "Your account, domains, scans, watched APIs and notifications: until you delete your account.",
                        "Guest sessions and their scans: 30 days.",
                        "Accounts that never confirm their email, and their scans: 7 days after signing up.",
                        "Email codes: until used or replaced; expired ones within a day.",
                        "The record of emails we send: 90 days.",
                        "Report feedback: kept without your account or the scanned address once its scan is gone.",
                        "Server logs: a short time, set by our hosting provider.",
                        "Payment records, once payments exist: as long as tax law requires.",
                        "Emails: as long as needed to help you.",
                    ],
                ],
            },
            {
                h: "your rights",
                body: [
                    "You can ask to see the data we hold about you, correct it, delete it, get a copy to take elsewhere, or object to or restrict how we use it. Email {email} from the address on your account, and we'll answer within 30 days. If you live in the European Union or the UK, you can also complain to your local data protection authority.",
                ],
            },
            {
                h: "security",
                body: [
                    "Everything travels over HTTPS, passwords are hashed, the data sits in EU data centres, and access is limited to the person who runs xikomu. No system is perfectly secure; if something goes wrong that affects your data, we'll tell you.",
                    "Found a security problem in xikomu itself? Please email {securityEmail} before making it public.",
                ],
            },
            {
                h: "children",
                body: ["xikomu is for people who build and run APIs. It isn't meant for anyone under 16."],
            },
            {
                h: "changes",
                body: [
                    "When this policy changes, so does the date at the top. For significant changes, we'll tell registered users before they apply.",
                ],
            },
        ],
    },

    refunds: {
        meta: "refunds | xikomu",
        description:
            "xikomu's refund policy: a full refund of any Pro payment within 14 days, no questions asked, and cancel anytime.",
        title: "refunds",
        heading: "refund policy",
        updated: UPDATED,
        intro: ["Pro isn't on sale yet. When it is, this is how refunds work."],
        sections: [
            {
                h: "14 days, full refund",
                body: [
                    "If Pro isn't right for you, email {email} within 14 days of a payment, your first or any renewal, and we'll refund that payment in full. No questions asked.",
                ],
            },
            {
                h: "how it works",
                body: [
                    [
                        "Write from the email address on your account, or reply to your Paddle receipt.",
                        "Paddle, our merchant of record, sends the refund to the card or account you paid with. Your bank may take a few days to show it.",
                        "A refund ends that month of Pro, and your account goes back to the free plan. Your data stays.",
                    ],
                ],
            },
            {
                h: "after 14 days",
                body: [
                    "We don't refund part of a month, but you can cancel at any time: Pro stays active until the end of the month you've paid for, and you won't be charged again.",
                ],
            },
            {
                h: "your rights",
                body: [
                    "This policy doesn't take away any rights you have under consumer law where you live. The free plan costs nothing, so there's nothing to refund there.",
                ],
            },
        ],
    },
};
