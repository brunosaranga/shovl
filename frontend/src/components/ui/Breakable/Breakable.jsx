import { Fragment } from "react";

// Long hostnames and addresses: lets a line break after a dot or a slash
// (api.<wbr>example.<wbr>com/<wbr>v1), so a narrow screen never splits "example" in two.
// Pair it with overflow-wrap: break-word, which only steps in for one piece too long to fit.
export default function Breakable({ text }) {
    const parts = [];
    let current = "";
    for (const char of String(text ?? "")) {
        current += char;
        if (char === "." || char === "/") {
            parts.push(current);
            current = "";
        }
    }
    if (current) parts.push(current);

    return parts.map((part, index) => (
        <Fragment key={index}>
            {part}
            {index < parts.length - 1 ? <wbr /> : null}
        </Fragment>
    ));
}
