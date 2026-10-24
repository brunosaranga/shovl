// FAQ modal. Desktop: the "?" button in the bottom-right corner. Mobile: "faq" in the account menu.
// In answers, `backticks` become inline code and {email} becomes a mailto link to common.contactEmail.
// Keep answers in step with the backend: limits in scans/limits.py, session length in core/settings.py,
// shovl watch's slots and cadence in accounts/plans.py (the free cadence is WATCH_FREE_CADENCE_DAYS,
// weekly during the beta), its three tries in watch/models.py (MAX_FAILURES).
export const faq = {
    title: "faq",
    open: "open the faq",
    close: "close the faq",
    footer: "still stuck? email {email}",

    sections: [
        {
            title: "about shovl",
            items: [
                {
                    q: "what does shovl do?",
                    a: "it runs six checks against an API address you give it: authentication, object-level access (BOLA), mass assignment, rate limiting, misconfiguration and data exposure. you get a report with a severity for each.",
                },
                {
                    q: "will a scan harm my API?",
                    a: "on your own domain, shovl only reads. the one check that sends data, mass assignment, is skipped there. the rate-limit test sends up to 15 quick requests and stops as soon as your API pushes back.",
                },
                {
                    q: "why can't I scan any address I like?",
                    a: "guests can scan practice targets only. your own domains need a free account and proof that you own the domain (a DNS TXT record). private and internal network addresses are always refused.",
                },
                {
                    q: "what are practice targets?",
                    a: "free public test APIs anyone can scan: postman-echo.com, httpbingo.org, jsonplaceholder.typicode.com and dummyjson.com. they echo or fake their writes, so nothing gets stored. shovl treats them like any other API, so the results are real.",
                },
            ],
        },
        {
            title: "results",
            items: [
                {
                    q: "what do the severities mean?",
                    a: "high: strong evidence of a real problem, like an invalid token getting through. medium: something is open to anyone and shovl can't tell if that's on purpose. low: something couldn't be verified or assessed. could not run: the check didn't finish, which says nothing about your API.",
                },
                {
                    q: "why does my public API show medium?",
                    a: "an endpoint that answers without a login might be public on purpose. shovl can't know that, so it flags it for you to judge.",
                },
                {
                    q: "why is my rate limiting medium?",
                    a: "the test stops at 15 requests, so a higher limit won't show up. advertise your limit in response headers (`RateLimit-*` or `X-RateLimit-*`) and the check passes.",
                },
                {
                    q: "why does my report say \"based on 5 of 6 checks\"?",
                    a: "mass assignment sends data to your API, so it only runs on practice targets. on your own domain it's skipped and the report says so. a check that couldn't finish is left out of the count too.",
                },
                {
                    q: "what do the three knobs do?",
                    a: "each one adds to the report. generate report opens it on the full per-check breakdown instead of the summary. suggest fix adds a fix for every problem, even on the summary. verbose shows the live log while the scan runs and keeps the raw responses in the breakdown. the breakdown is always saved, so \"show full report\" opens it later without using up a scan.",
                },
                {
                    q: "can I download a report?",
                    a: "yes. every finished report has a \"download pdf\" button. the PDF has the score, every finding with its fix when suggest fix was on, and what changed since your last scan, ready to hand to a client or a teammate. it's free during the beta and doesn't use up a scan.",
                },
                {
                    q: "what does \"since your last scan\" show?",
                    a: "scan the same address again and the report compares it with your last finished scan of it: which checks got fixed, which got better or worse, and which are new problems. http and https count as the same address, so moving to HTTPS shows up as a fix.",
                },
                {
                    q: "why did my scan fail?",
                    a: "shovl couldn't reach the API: the address wasn't found, the connection was refused or timed out, the certificate was invalid, or it redirected to another site. the report says which. failed scans don't count against your allowance.",
                },
                {
                    q: "can I close the tab while a scan runs?",
                    a: "not yet. leaving the page stops the scan. stopped scans don't count against your allowance.",
                },
                {
                    q: "what does pause do?",
                    a: "the check that's running finishes, then the scan holds and nothing more is sent to the API until you resume. a scan paused for 5 minutes in total stops on its own. a paused scan still counts against your allowance; a stopped one doesn't.",
                },
            ],
        },
        {
            title: "shovl watch",
            items: [
                {
                    q: "what is shovl watch?",
                    a: "shovl watch re-scans your API on a schedule and tells you when something gets worse. it starts by itself when a scan of one of your own verified domains finishes and your plan has room. what it finds lands in the bell (on a phone: \"notifications\" in the account menu).",
                },
                {
                    q: "how often does it scan?",
                    a: "a free account watches one API: every week during the beta, every month after it. Pro, coming later, watches five APIs every week. settings shows when each one is next due.",
                },
                {
                    q: "why does the free plan watch only one API?",
                    a: "every watched API is a scan we run on our own servers, week after week. one is enough to see it working. to watch a different API, open its report and choose \"watch this one instead\": no extra scan runs, and the other API stops being watched.",
                },
                {
                    q: "do scheduled scans use up my allowance?",
                    a: "no. they're tagged \"watch\" on your dashboard and don't count toward your daily scans. they run the same read-only checks as any scan of your own domain, so mass assignment stays off.",
                },
                {
                    q: "when do I get an alert?",
                    a: "when a scheduled scan finds a new problem, a check that got worse, or a higher risk score than the scan before it. the alert in the bell lists what changed and opens the report. no change, no alert: the scan still shows on your dashboard.",
                },
                {
                    q: "why should I keep the verification record?",
                    a: "before every scheduled scan, shovl checks that your DNS record (or file) is still there. if it's missing three times in a row, an hour or more apart, the domain goes back to pending, its watches pause and the bell asks you to verify it again. verifying restarts them; until then, scans you start of that domain need it verified too.",
                },
                {
                    q: "how do I turn it off?",
                    a: "in settings, under shovl watch: one switch stops every scheduled scan, and each watched API has its own. \"mute the bell\" keeps the scans running but stops news from adding to the bell's count. things that need you, like a paused watch, still count.",
                },
                {
                    q: "what's the unverified cache?",
                    a: "domains you started verifying but didn't finish, plus any that lost verification. it's folded under verified domains in settings: remove them one at a time, or empty it. removing a domain also ends any watch on it. the bell lists them too, with a verify button.",
                },
            ],
        },
        {
            title: "your account",
            items: [
                {
                    q: "how many scans do I get?",
                    a: "guests get 3 free scans in total, on practice targets only. a free account gets 5 scans per rolling 24 hours, on practice targets and your own verified domains. scheduled scans by shovl watch don't count.",
                },
                {
                    q: "what happens to my guest scans?",
                    a: "they're kept for 30 days. create a free account, or sign in to one you have, and they move there for good. scans you ran today still count toward today's total.",
                },
                {
                    q: "why was I signed out?",
                    a: "sessions last 16 hours during the beta. sign in again and everything is where you left it.",
                },
                {
                    q: "I forgot my password.",
                    a: "there's no reset yet. email {email} from the address you signed up with and we'll sort it out.",
                },
                {
                    q: "does shovl send emails?",
                    a: "not during the beta: shovl watch's alerts land in the bell. if you write to us, we reply from {email}. any other email claiming to be shovl isn't from us.",
                },
                {
                    q: "can I delete my account?",
                    a: "yes. email {email} from the address you signed up with and we'll delete it, with your scans and domains.",
                },
                {
                    q: "why is the first page load slow?",
                    a: "the beta runs on a free server that sleeps when nobody's using it. the first visit after a quiet spell can take about a minute while it wakes up.",
                },
                {
                    q: "where is my data stored?",
                    a: "on servers in Frankfurt, Germany: your email, a hashed password, your domains, your scan results, the APIs shovl watch scans for you, the bell's notifications, and any answer you give under a report. guest sessions and their scans are deleted after 30 days. when a scan is deleted, an answer given under it stays, without your account or the scanned address.",
                },
            ],
        },
    ],
};
