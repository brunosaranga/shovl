// Fallback messages. The backend's own messages are plain language and shown first;
// these are used when a response has no message (or no response came back at all).
export const errors = {
    generic: "something went wrong. try again.",
    network: "can't reach xikomu right now. check your connection and try again.",

    codes: {
        registration_required: "Create a free account to scan your own domain.",
        guest_limit_reached: "You've used your free scans. Create a free account to keep going.",
        daily_limit_reached: "You've used today's scans. Try again once the next one frees up.",
        too_many_attempts: "Too many scan attempts today. Try again later.",
        too_many_sessions: "Too many new sessions from your network. Try again later, or create a free account.",
        domain_not_verified: "Verify ownership of this domain before scanning it.",
        tos_required: "Agree to the terms of service before scanning.",
        token_revoked: "This session is no longer valid. Please sign in again.",
        bad_request: "xikomu couldn't use that URL. Include http:// or https://",
        // Confirming the email (the code screen). The backend sends its own wording first.
        email_unconfirmed: "Confirm your email first: type the 6-digit code we sent you.",
        code_invalid: "Type the 6 digits from the email.",
        code_wrong: "That code isn't right.",
        code_used_up: "That code isn't right, and it was the last try. Ask for a new code.",
        code_expired: "That code has expired. Ask for a new one.",
        code_cooldown: "Wait a moment before asking for another code.",
        code_limit: "That's as many codes as we can send for now. Try again tomorrow.",
        address_limit: "That's as many different addresses as one account can try in a day.",
        email_failed: "We couldn't send the code just now. Try again in a few minutes.",
        link_invalid: "This link isn't valid. You can turn murindzi's emails off in settings.",
    },
};
