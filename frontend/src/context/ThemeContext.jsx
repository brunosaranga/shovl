import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

// Light or dark. index.html already put data-theme on <html> before React loaded;
// this keeps it in sync and remembers the visitor's choice.
const STORAGE_KEY = "shovl.theme";
const ThemeContext = createContext(null);

function readInitialTheme() {
    return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function ThemeProvider({ children }) {
    const [theme, setTheme] = useState(readInitialTheme);

    useEffect(() => {
        document.documentElement.dataset.theme = theme;
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch {
            // storage unavailable (private mode): the theme still works for this visit
        }
    }, [theme]);

    const toggleTheme = useCallback(() => {
        setTheme((previous) => (previous === "dark" ? "light" : "dark"));
    }, []);

    const value = useMemo(() => ({ theme, setTheme, toggleTheme }), [theme, toggleTheme]);
    return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
    const ctx = useContext(ThemeContext);
    if (!ctx) {
        throw new Error("useTheme must be used inside <ThemeProvider>");
    }
    return ctx;
}
