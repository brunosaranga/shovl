// Reads a server-sent-events body and yields each `data: {...}` payload as an object.
// Frames are separated by a blank line; partial chunks are buffered until complete.
export async function* readEvents(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let separator;
        while ((separator = buffer.indexOf("\n\n")) !== -1) {
            const frame = buffer.slice(0, separator);
            buffer = buffer.slice(separator + 2);

            for (const line of frame.split("\n")) {
                const trimmed = line.trim();
                if (!trimmed.startsWith("data:")) continue;
                const payload = trimmed.slice(5).trim();
                if (!payload) continue;
                try {
                    yield JSON.parse(payload);
                } catch {
                    // keep-alive or non-JSON line: ignore
                }
            }
        }
    }
}

/** A refused stream answers with a plain JSON body (sent as text/event-stream). */
export async function readJsonBody(response) {
    try {
        return JSON.parse(await response.text());
    } catch {
        return {};
    }
}
