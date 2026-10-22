/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {FileInput} from "@web/core/file_input/file_input";

// Expose two optional lifecycle hooks around the HTTP upload so parents
// (e.g. Many2ManyBinaryField) can render a spinner/overlay while the
// request is in flight. `finally` ensures the "after" hook also fires
// when FileInput.uploadFiles rejects (envelope-level error), avoiding a
// stuck overlay. FileInput.props already declares `"*": true`, so these
// extra props validate without a schema edit; they are also no-ops for
// callers that do not pass them.
patch(FileInput.prototype, "web_attachment_document_type.FileInput", {
    async onFileInputChange() {
        if (this.props.onBeforeUpload) {
            this.props.onBeforeUpload();
        }
        try {
            await this._super(...arguments);
        } finally {
            if (this.props.onAfterUpload) {
                this.props.onAfterUpload();
            }
        }
    },
});
