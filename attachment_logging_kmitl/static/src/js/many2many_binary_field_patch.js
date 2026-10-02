/** @odoo-module **/

import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

// The default widget's × button only issues an m2m FORGET, leaving the
// ir.attachment record orphaned (still on disk, still linked via
// res_model/res_id, invisible to _delete_and_notify — so OCA
// attachment_logging never fires). Route the click through the same JSON
// endpoint the chatter uses, so the attachment is actually deleted and the
// audit note is posted.
patch(Many2ManyBinaryField.prototype, "attachment_logging_kmitl.Many2ManyBinaryField", {
    setup() {
        this._super(...arguments);
        this.rpc = useService("rpc");
    },

    async onFileRemove(deleteId) {
        const record = this.props.value.records.find(
            (r) => r.data.id === deleteId
        );
        try {
            await this.rpc("/mail/attachment/delete", {attachment_id: deleteId});
        } catch (error) {
            // Fall through to the standard FORGET so the UI stays in sync —
            // OCA log will not fire in this branch, but the user still sees
            // the file removed from the form.
            console.error("attachment_logging_kmitl: delete failed", error);
        }
        this.operations.removeRecord(record);
    },
});
