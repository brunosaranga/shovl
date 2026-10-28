// A forgotten password (pages/ResetPassword). The numbers (15 minutes, 5 tries) are the
// backend's (backend/shovl/accounts/reset.py); keep them in step.
export const reset = {
    meta: "reset your password | xikomu",
    pageTitle: "password",

    ask: {
        title: "forgot your password?",
        lead: "type the address you signed up with. we'll email it a 6-digit code to choose a new password.",
        email: "Email",
        emailPlaceholder: "you@company.com",
        submit: "email me a code",
        busy: "sending...",
    },

    code: {
        title: "check your inbox.",
        // {email} is set apart on the page.
        lead: "if an account uses {email}, we've emailed it a code. it works for 15 minutes.",
        note: "choosing a new password signs you out everywhere else.",
        code: "6-digit code",
        password: "New password",
        passwordHint: "at least 10 characters. not a common password, not all numbers, not your email.",
        submit: "set new password",
        busy: "saving...",
        done: "done.",
    },

    resend: {
        idle: "send a new code",
        wait: "send a new code in {seconds}s",
        busy: "sending...",
        done: "new code sent. only the newest one works.",
    },
    spam: "nothing yet? check your spam folder.",
    other: "use a different address",
    back: "back to sign in",
};
