import { useEffect, useState } from "react";

export const MOBILE_QUERY = "(max-width: 768px)";

// True while the media query matches. Usage: const isMobile = useMediaQuery(MOBILE_QUERY)
export function useMediaQuery(query) {
    const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

    useEffect(() => {
        const list = window.matchMedia(query);
        const onChange = () => setMatches(list.matches);
        onChange();
        list.addEventListener("change", onChange);
        return () => list.removeEventListener("change", onChange);
    }, [query]);

    return matches;
}
