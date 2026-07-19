/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";

const { onMounted, useState } = owl;

/**
 * Form controller for sarabun.document. Two behaviours:
 *
 * 1. Marks the current user's routing-step recipient as "read" (เปิดอ่านแล้ว) when
 *    the หนังสือ is opened (best-effort RPC on mount).
 * 2. An in-form PDF preview (ADR-0007): once the หนังสือ has been sent (state !=
 *    draft) the official PDF is shown by default in an <iframe> instead of the form;
 *    a control-panel button toggles between the PDF preview and the editable form,
 *    both ways. A draft defaults to the form but keeps the toggle so it can be
 *    previewed before sending.
 *
 * Wired via js_class="sarabun_document_form" on the form view.
 */
export class SarabunDocumentFormController extends FormController {
    static template = "agx_sarabun.SarabunDocumentFormView";

    setup() {
        super.setup();
        this.sarabunOrm = useService("orm");
        // null = follow the state-driven default; true/false = the user's explicit choice.
        this.sarabunPreview = useState({ mode: null });
        onMounted(() => {
            const resId = this.model.root.resId;
            if (resId) {
                this.sarabunOrm
                    .call("sarabun.document", "action_mark_read", [[resId]])
                    .catch(() => {});
            }
        });
    }

    get showPreview() {
        if (!this.model.root.resId) {
            return false; // a fresh/unsaved draft has nothing to preview
        }
        if (this.sarabunPreview.mode !== null) {
            return this.sarabunPreview.mode;
        }
        // Default: preview once the หนังสือ has been sent (state != draft).
        const state = this.model.root.data.state;
        return Boolean(state) && state !== "draft";
    }

    get sarabunPreviewUrl() {
        return `/sarabun/document/${this.model.root.resId}/pdf?inline=1`;
    }

    toggleSarabunPreview() {
        this.sarabunPreview.mode = !this.showPreview;
    }

    get className() {
        const result = super.className;
        result["o_sarabun_previewing"] = this.showPreview;
        return result;
    }
}

export const sarabunDocumentFormView = {
    ...formView,
    Controller: SarabunDocumentFormController,
};

registry.category("views").add("sarabun_document_form", sarabunDocumentFormView);
