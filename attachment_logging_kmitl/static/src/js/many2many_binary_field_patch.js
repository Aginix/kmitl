/** @odoo-module **/

import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {session} from "@web/session";
import {_t} from "@web/core/l10n/translation";

// The default widget's × button only issues an m2m FORGET, leaving the
// ir.attachment record orphaned (still on disk, still linked via
// res_model/res_id, invisible to _delete_and_notify — so OCA
// attachment_logging never fires). Route the click through the same JSON
// endpoint the chatter uses, so the attachment is actually deleted and the
// audit note is posted. Only active when the OCA logging toggle is on.
patch(Many2ManyBinaryField.prototype, "attachment_logging_kmitl.Many2ManyBinaryField", {
    setup() {
        this._super(...arguments);
        this.rpc = useService("rpc");
        this.notification = useService("notification");
    },

    async onFileRemove(deleteId) {
        if (!session.attachment_logging_kmitl_enabled) {
            return this._super(...arguments);
        }
        const record = this.props.value.records.find(
            (r) => r.data.id === deleteId
        );
        if (!record) {
            return;
        }
        try {
            await this.rpc("/mail/attachment/delete", {attachment_id: deleteId});
        } catch (error) {
            this.notification.add(
                _t("Could not delete the attachment. It has not been removed."),
                {type: "danger"}
            );
            console.error("attachment_logging_kmitl: delete failed", error);
            return;
        }
        this.operations.removeRecord(record);
    },
});
