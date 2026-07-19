/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

const { Component } = owl;

/**
 * Full-page PDF preview of a sarabun.document — a client action opened from the
 * document form's "ดูเอกสาร (PDF)" button (ADR-0007). Shows the official PDF (served
 * live before completion, frozen after) in an <iframe>, with a back button to the
 * form. The document id/name arrive via the action's `params`.
 */
export class SarabunPdfPreview extends Component {
    setup() {
        const params = (this.props.action && this.props.action.params) || {};
        this.docId = params.doc_id;
        this.docName = params.doc_name || "";
    }

    get pdfUrl() {
        return `/sarabun/document/${this.docId}/pdf?inline=1`;
    }

    goBack() {
        // Odoo mirrors the action stack in browser history, so going back restores
        // the document form we came from (clean breadcrumb, no duplicate controller).
        browser.history.back();
    }
}
SarabunPdfPreview.template = "agx_sarabun.SarabunPdfPreview";

registry.category("actions").add("sarabun_pdf_preview", SarabunPdfPreview);
