// Fallback messages. The backend's own messages are plain language and shown first;
// these are used when a response has no message (or no response came back at all).
export const errors = {
    generic: "something went wrong. try again.",
    network: "can't reach shovl right now. check your connection and try again.",

    codes: {
        registration_required: "Create a free account to scan your own domain.",
        guest_limit_reached: "You've used your free scans. Create a free account to keep going.",
        daily_limit_reached: "You've used today's scans. Try again once the next one frees up.",
        too_many_attempts: "Too many scan attempts today. Try again later.",
        too_many_sessions: "Too many new sessions from your network. Try again later, or create a free account.",
        domain_not_verified: "Verify ownership of this domain before scanning it.",
        tos_required: "Agree to the terms of service before scanning.",
        token_revoked: "This session is no longer valid. Please sign in again.",
        bad_request: "shovl couldn't use that URL. Include http:// or https://",
    },
};
