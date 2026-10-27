import { useEffect, useState } from "react";

// Whole seconds left until `until` (a Date.now()-style number), ticking once a second; 0 when
// it has passed or there's nothing to wait for.
export function useCountdown(until) {
    const [now, setNow] = useState(() => Date.now());

    useEffect(() => {
        if (!until) return undefined;
        const tick = () => setNow(Date.now());
        // Straight away too: `now` may be from long ago if the last countdown ended a while back.
        const first = setTimeout(tick, 0);
        const timer = setInterval(() => {
            tick();
            if (Date.now() >= until) clearInterval(timer);
        }, 1000);
        return () => {
            clearTimeout(first);
            clearInterval(timer);
        };
    }, [until]);

    return until ? Math.max(0, Math.ceil((until - now) / 1000)) : 0;
}
