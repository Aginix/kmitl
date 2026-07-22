/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const { Component } = owl;

/**
 * PDF preview of a sarabun.document's official PDF (served live before completion,
 * frozen after) — ADR-0007. Two surfaces:
 *
 * - SarabunPdfInline: a view widget (<widget name="sarabun_pdf_inline"/>) embedded
 *   in the form, before the เนื้อหา section, shown once the หนังสือ has been sent.
 * - SarabunPdfPreview: a client action opened as a dialog from the draft
 *   "ดูตัวอย่างเอกสาร" button (draft has no inline preview yet).
 *
 * Both render the same controller URL (?inline=1 so the browser displays it).
 */
export class SarabunPdfInline extends Component {
    get docId() {
        return this.props.record.resId;
    }
    get previewUrl() {
        return `/sarabun/document/${this.docId}/preview`;
    }
}
SarabunPdfInline.template = "agx_sarabun.SarabunPdfInline";
SarabunPdfInline.props = { ...standardWidgetProps };

registry.category("view_widgets").add("sarabun_pdf_inline", SarabunPdfInline);

export class SarabunPdfPreview extends Component {
    setup() {
        const params = (this.props.action && this.props.action.params) || {};
        this.docId = params.doc_id;
    }
    get previewUrl() {
        return `/sarabun/document/${this.docId}/preview`;
    }
}
SarabunPdfPreview.template = "agx_sarabun.SarabunPdfPreview";
SarabunPdfPreview.props = ["*"];

registry.category("actions").add("sarabun_pdf_preview", SarabunPdfPreview);
