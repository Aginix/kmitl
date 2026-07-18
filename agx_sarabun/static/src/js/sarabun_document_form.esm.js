/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";

const { onMounted } = owl;

/**
 * Form controller for sarabun.document that marks the current user's routing-step
 * recipient as "read" (เปิดอ่านแล้ว) when the หนังสือ is opened. Wired via
 * js_class="sarabun_document_form" on the form view. Best-effort: a failed RPC
 * never blocks opening the document.
 */
export class SarabunDocumentFormController extends FormController {
    setup() {
        super.setup();
        this.sarabunOrm = useService("orm");
        onMounted(() => {
            const resId = this.model.root.resId;
            if (resId) {
                this.sarabunOrm
                    .call("sarabun.document", "action_mark_read", [[resId]])
                    .catch(() => {});
            }
        });
    }
}

export const sarabunDocumentFormView = {
    ...formView,
    Controller: SarabunDocumentFormController,
};

registry.category("views").add("sarabun_document_form", sarabunDocumentFormView);
