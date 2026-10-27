// The code screen (pages/ConfirmEmail): an account confirms its email before anything else
// opens. The numbers (15 minutes, 7 days, 5 tries) are the backend's
// (backend/shovl/accounts/confirmation.py); keep them in step.
export const confirm = {
    meta: "confirm your email | xikomu",
    pageTitle: "confirm email",
    loading: "loading...",

    title: "check your inbox.",
    sent: "we sent a 6-digit code to {email}. it works for 15 minutes.",
    notSent: "we'll email a 6-digit code to {email} to make sure it's yours.",
    why: "xikomu only scans your domains, watches your APIs and emails you once your address is confirmed.",
    // {date}: when an account that signed up is deleted if it hasn't confirmed.
    deadline: "confirm by {date}, or this account is deleted.",

    code: {
        label: "6-digit code",
        submit: "confirm",
        busy: "checking...",
        done: "confirmed.",
    },
    send: {
        idle: "email me the code",
        busy: "sending...",
    },
    resend: {
        idle: "send a new code",
        wait: "send a new code in {seconds}s",
        busy: "sending...",
        done: "new code sent. only the newest one works.",
    },
    spam: "nothing yet? check your spam folder.",

    change: {
        toggle: "wrong address? change it",
        title: "change the address",
        email: "New email",
        password: "Your password",
        passwordHint: "the one you chose when signing up.",
        submit: "send the code there",
        busy: "sending...",
        cancel: "cancel",
        done: "address changed. the code is on its way to {email}.",
        notSent: "address changed to {email}, but the code didn't go out. {reason}",
    },

    signOut: "not you? log out",
};
