// Per-page <title>. React 19 moves <title> into <head> on its own, so no helmet library.
export default function PageMeta({ title }) {
    return title ? <title>{title}</title> : null;
}
