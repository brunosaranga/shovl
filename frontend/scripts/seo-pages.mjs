// Runs after `vite build` (npm run build). Search engines and link previews (WhatsApp,
// LinkedIn) read a page's <head> without running JavaScript, and the app has one index.html
// for every address. So this writes a copy per public page, with that page's own title,
// description, canonical address and preview tags:
//
//     dist/pricing/index.html, dist/terms/index.html, dist/privacy/index.html, ...
//
// Render serves dist/pricing/index.html at /pricing (and /pricing/), before the rewrite to
// /index.html that the app's other addresses use. The body is the same app, so the page works
// exactly as before. It also writes dist/sitemap.xml with the same list (public/robots.txt
// points at it).
//
// The words come from content/en (`meta` is the title, `description` the description); the
// landing's own <head> is index.html itself. To add a public page: add it to PAGES.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { landing } from "../src/content/en/landing.js";
import { legal } from "../src/content/en/legal.js";
import { pricing } from "../src/content/en/pricing.js";

const SITE = "https://shovll.com";
const DIST = join(dirname(fileURLToPath(import.meta.url)), "..", "dist");

const PAGES = [
    { path: "/pricing", title: pricing.meta, description: pricing.description },
    { path: "/terms", title: legal.terms.meta, description: legal.terms.description },
    { path: "/privacy", title: legal.privacy.meta, description: legal.privacy.description },
    { path: "/refunds", title: legal.refunds.meta, description: legal.refunds.description },
];

const escape = (text) =>
    String(text).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// Replace exactly one tag, or stop the build: a tag that went missing from index.html would
// otherwise leave a page with the landing's title or address without anyone noticing.
function swap(html, pattern, replacement, what) {
    const found = html.match(pattern) || [];
    if (found.length !== 1) {
        throw new Error(`seo-pages: expected one ${what} in dist/index.html, found ${found.length}`);
    }
    return html.replace(pattern, replacement);
}

const template = readFileSync(join(DIST, "index.html"), "utf8");

// The landing's <head> is index.html: check it still says what content/en/landing.js says.
if (!template.includes(`<title>${escape(landing.meta)}</title>`)) {
    throw new Error("seo-pages: index.html's <title> no longer matches landing.meta in content/en/landing.js");
}

for (const page of PAGES) {
    if (!page.title || !page.description) {
        throw new Error(`seo-pages: ${page.path} needs a meta and a description in content/en`);
    }
    const url = `${SITE}${page.path}`;
    const title = escape(page.title);
    const description = escape(page.description);

    let html = template;
    html = swap(html, /<title>[^<]*<\/title>/g, `<title>${title}</title>`, "<title>");
    html = swap(
        html,
        /<meta\s+name="description"\s+content="[^"]*"\s*\/>/g,
        `<meta name="description" content="${description}" />`,
        "description",
    );
    html = swap(html, /<link rel="canonical" href="[^"]*" \/>/g, `<link rel="canonical" href="${url}" />`, "canonical");
    html = swap(html, /<meta property="og:url" content="[^"]*" \/>/g, `<meta property="og:url" content="${url}" />`, "og:url");
    html = swap(
        html,
        /<meta property="og:title" content="[^"]*" \/>/g,
        `<meta property="og:title" content="${title}" />`,
        "og:title",
    );
    html = swap(
        html,
        /<meta property="og:description" content="[^"]*" \/>/g,
        `<meta property="og:description" content="${description}" />`,
        "og:description",
    );

    const folder = join(DIST, page.path.slice(1));
    mkdirSync(folder, { recursive: true });
    writeFileSync(join(folder, "index.html"), html);
}

const urls = ["/", ...PAGES.map((page) => page.path)];
const sitemap = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...urls.map((path) => `    <url><loc>${SITE}${path}</loc></url>`),
    "</urlset>",
    "",
].join("\n");
writeFileSync(join(DIST, "sitemap.xml"), sitemap);

console.log(`seo-pages: ${PAGES.length} pages and sitemap.xml (${urls.length} addresses)`);
