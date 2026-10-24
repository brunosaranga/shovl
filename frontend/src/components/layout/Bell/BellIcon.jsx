// The bell, filled. Muted: an outline with a slash through it.
export default function BellIcon({ muted = false, className = "" }) {
    const bell = "M12 2.5a1.6 1.6 0 0 1 1.6 1.6v.6a6.4 6.4 0 0 1 4.8 6.2v4.6l2.1 2.6H3.5l2.1-2.6v-4.6a6.4 6.4 0 0 1 4.8-6.2v-.6A1.6 1.6 0 0 1 12 2.5Z";
    return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className={className}>
            {muted ? (
                <>
                    <path d={bell} fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                    <path d="M3 3l18 18" stroke="currentColor" strokeWidth="2.4" strokeLinecap="square" />
                </>
            ) : (
                <path d={bell} fill="currentColor" />
            )}
            <path d="M9.6 19.6h4.8a2.4 2.4 0 0 1-4.8 0Z" fill="currentColor" />
        </svg>
    );
}
