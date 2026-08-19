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
    /**
     * Cache-busting token built from the routing-state fields the form already
     * loads. An <iframe> keeps its cached render whenever `src` is byte-identical,
     * so acting on a step — which reloads the form but not the URL — left the
     * preview stale: the fresh ลายเซ็น only appeared after a manual browser refresh.
     * Signatures are snapshotted onto the STEP rows (not the sarabun.document row),
     * so the document's write_date does NOT bump on an intermediate act; instead we
     * fold the routing signals that DO move — state, progress, ack backlog, and the
     * viewer's own signed / pending-step status — into the URL so it changes exactly
     * when the rendered preview could. The controller ignores the extra param (**kw).
     */
    get previewVersion() {
        const d = this.props.record.data;
        const activeStep = d.my_active_step_id;
        return [
            d.state,
            d.routing_progress,
            d.pending_ack_count,
            d.has_signed,
            activeStep && activeStep[0],
        ].join("-");
    }
    get previewUrl() {
        const v = encodeURIComponent(this.previewVersion);
        return `/sarabun/document/${this.docId}/preview?v=${v}`;
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
