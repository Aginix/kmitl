/** @odoo-module **/

import {CHANGED_EVENT} from "@agx_change_request/js/change_request_panel.esm";
import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

// The outstanding Change requests count our ir.attachment._attachment_format adds.
registerPatch({
    name: "Attachment",
    fields: {
        openRequestCount: attr({default: 0}),
    },
    recordMethods: {
        // Deleting a file cancels the requests pinned on it: refresh the form.
        async remove() {
            const hadRequests = Boolean(this.openRequestCount);
            await this._super(...arguments);
            if (hadRequests) {
                window.dispatchEvent(new CustomEvent(CHANGED_EVENT));
            }
        },
    },
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            if ("openRequestCount" in data) {
                data2.openRequestCount = data.openRequestCount;
            }
            return data2;
        },
    },
});
