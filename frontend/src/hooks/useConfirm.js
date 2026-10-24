import { useEffect, useState } from "react";

// "sure?" buttons: the first click arms, a second click within `ms` goes ahead, and after
// that the button quietly goes back. Returns [armed, setArmed].
export function useConfirm(ms = 4000) {
    const [armed, setArmed] = useState(false);

    useEffect(() => {
        if (!armed) return undefined;
        const timer = setTimeout(() => setArmed(false), ms);
        return () => clearTimeout(timer);
    }, [armed, ms]);

    return [armed, setArmed];
}
