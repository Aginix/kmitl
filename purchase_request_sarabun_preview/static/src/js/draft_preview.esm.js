/** @odoo-module **/

import { SarabunPdfPreview } from "@agx_sarabun/js/sarabun_pdf_preview.esm";
import { registry } from "@web/core/registry";

/**
 * The dry-run หนังสือ of a purchase request, in the same dialog as the
 * หนังสือ's own preview: only the URL differs.
 */
export class PurchaseRequestSarabunDraftPreview extends SarabunPdfPreview {
    get previewUrl() {
        return this.props.action.params.url;
    }
}

registry
    .category("actions")
    .add(
        "purchase_request_sarabun_draft_preview",
        PurchaseRequestSarabunDraftPreview
    );
