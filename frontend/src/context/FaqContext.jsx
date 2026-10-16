import { createContext, useCallback, useContext, useMemo, useState } from "react";

// Whether the FAQ modal is open. Layout renders the modal and the desktop "?" button;
// the account menu opens it on mobile. State only: no UI lives in here.
const FaqContext = createContext(null);

export function FaqProvider({ children }) {
    const [isOpen, setIsOpen] = useState(false);

    const openFaq = useCallback(() => setIsOpen(true), []);
    const closeFaq = useCallback(() => setIsOpen(false), []);

    const value = useMemo(() => ({ isOpen, openFaq, closeFaq }), [isOpen, openFaq, closeFaq]);
    return <FaqContext.Provider value={value}>{children}</FaqContext.Provider>;
}

export function useFaq() {
    const ctx = useContext(FaqContext);
    if (!ctx) {
        throw new Error("useFaq must be used inside <FaqProvider>");
    }
    return ctx;
}
