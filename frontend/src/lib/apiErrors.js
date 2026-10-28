// Turns an axios error (or a refused stream body) into something a component can show:
//   { status, code, message, fields: { email: [...], password: [...] }, retryAfter }
// Backend messages are plain language, so they are used first; content/en/errors.js
// fills the gaps.

const FIELD_NAMES = ["email", "password", "hostname", "tos_agreed", "first_name", "consent"];

function deriveCode(status, body) {
    if (body?.code) return body.code;
    if (status === 403 && /domain not verified/i.test(body?.error || "")) return "domain_not_verified";
    if (status === 403 && /terms of service/i.test(body?.error || "")) return "tos_required";
    if (status === 400) return "bad_request";
    return null;
}

const asList = (value) => (Array.isArray(value) ? value.map(String) : value ? [String(value)] : []);

/** Shape a response body + status. Used for axios errors and refused streams alike. */
export function describeResponse(status, body, errors) {
    const code = deriveCode(status, body);
    const fields = {};
    FIELD_NAMES.forEach((name) => {
        const list = asList(body?.[name]);
        if (list.length) fields[name] = list;
    });

    // With field errors, those ARE the message (shown under each field); only a
    // server-provided detail goes on top. Without them, fall back to the code's copy.
    const hasFields = Object.keys(fields).length > 0;
    const nonField = asList(body?.non_field_errors);
    const serverMessage = body?.detail || body?.error || nonField[0] || null;
    const message = hasFields ? serverMessage : serverMessage || (code && errors.codes[code]) || errors.generic;

    return {
        status,
        code,
        message: typeof message === "string" ? message : message ? String(message) : null,
        fields,
        retryAfter: body?.retry_after || null,
    };
}

/** For axios errors: no response at all means the network or the server is down. */
export function describeError(error, errors) {
    if (!error?.response) {
        return { status: 0, code: "network", message: errors.network, fields: {}, retryAfter: null };
    }
    return describeResponse(error.response.status, error.response.data, errors);
}
