// Saving a file the API sent (the PDF report). The request needs the Authorization header,
// so it can't be a plain link: lib/api.js fetches it as a Blob, and this hands it to the
// browser as a download through a temporary link.

/** Starts a download of `blob` named `filename`. */
export function saveBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
    // Some browsers read the file after click() returns: give them a moment.
    setTimeout(() => URL.revokeObjectURL(url), 30000);
}

/** The file name from a Content-Disposition header, or `fallback`. */
export function filenameFrom(disposition, fallback) {
    const match = /filename="?([^";]+)"?/i.exec(disposition || "");
    const name = match?.[1]?.trim();
    // Only plain names: no folders, nothing hidden.
    return name && /^[\w.-]+$/.test(name) && !name.startsWith(".") ? name : fallback;
}

/**
 * An error answer to a Blob request arrives as a Blob too. Returns its JSON body
 * ({ detail, code }), or {} when there is none.
 */
export async function blobErrorBody(error) {
    const data = error?.response?.data;
    if (!(data instanceof Blob)) return data && typeof data === "object" ? data : {};
    try {
        return JSON.parse(await data.text());
    } catch {
        return {};
    }
}
