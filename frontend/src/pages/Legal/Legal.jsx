import PageMeta from "../../components/layout/PageMeta/PageMeta";
import NavCenter from "../../components/layout/NavCenter/NavCenter";
import PageBody from "../../components/layout/PageBody/PageBody";
import PageTitle from "../../components/ui/PageTitle/PageTitle";
import LegalDoc from "../../components/sections/legal/LegalDoc/LegalDoc";
import { useContent } from "../../hooks/useContent";

// /terms, /privacy and /refunds (routes.jsx). `doc` picks the document in content/en/legal.js.
export default function Legal({ doc }) {
    const { legal } = useContent();
    const page = legal[doc];

    return (
        <>
            <PageMeta title={page.meta} />
            <NavCenter>
                <PageTitle>{page.title}</PageTitle>
            </NavCenter>

            <PageBody width="narrow" gap="md">
                <LegalDoc doc={page} />
            </PageBody>
        </>
    );
}
