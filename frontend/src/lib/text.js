// Fills {placeholders} in copy from content/: fill("{n} left", { n: 3 }) → "3 left".
export function fill(template, values = {}) {
    return String(template).replace(/\{(\w+)\}/g, (match, key) =>
        values[key] === undefined || values[key] === null ? match : String(values[key])
    );
}

export function formatDate(iso) {
    if (!iso) return "—";
    const date = new Date(iso);
    return Number.isNaN(date.getTime())
        ? "—"
        : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function formatDateTime(iso) {
    if (!iso) return "—";
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

// "just now", "5 min ago", "3 hours ago", "2 days ago", then the date.
export function formatAgo(iso, now = Date.now()) {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const minutes = Math.floor((now - date.getTime()) / 60000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return hours === 1 ? "1 hour ago" : `${hours} hours ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return days === 1 ? "yesterday" : `${days} days ago`;
    return formatDate(iso);
}

export function formatTime(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    return Number.isNaN(date.getTime())
        ? ""
        : date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}
