import { en } from "./en";

// Add another language as content/<code>/index.js with the same shape, then list it here.
export const content = {
    en,
};

export const defaultLocale = "en";
export const locales = Object.keys(content);
