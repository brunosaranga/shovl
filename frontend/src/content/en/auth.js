export const auth = {
    meta: {
        signin: "sign in | shovl",
        register: "register | shovl",
    },

    intro: {
        title: "Securing your APIs from commit to production.",
        // The image itself is imported in AuthIntro.jsx; only its text lives here.
        graphicAlt: "illustration of an incident report",
    },

    tabs: {
        signin: "sign in",
        register: "register",
    },

    fields: {
        email: "Email",
        emailPlaceholder: "you@company.com",
        password: "Password",
        passwordHint: "at least 10 characters. not a common password, not all numbers, not your email.",
    },

    // [label](/path) becomes a link (opens in a new tab here).
    consent: "I own or have explicit permission to test any URL I submit to shovl, and I accept the [terms](/terms) and [privacy policy](/privacy)",

    submit: {
        signin: "Sign In",
        register: "Register",
        busy: "loading...",
    },

    // Shown when the visitor already has a guest session.
    guest: {
        register: "your guest scans move to your new account.",
        signin: "signing in moves your guest scans to your account.",
    },

    // Why the visitor was sent here (location.state.notice).
    notices: {
        registerForOwnDomain: "create a free account to scan your own domain. practice targets stay free without one.",
        registerToContinue: "create a free account to continue.",
        expired: "your session ended. sign in again.",
    },
};