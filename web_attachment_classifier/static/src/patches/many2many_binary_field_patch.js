/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {onWillStart, useState} from "@odoo/owl";
import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {AttachmentClassifierDialog} from "@web_attachment_classifier/components/attachment_classifier_dialog";

// Ensure the doctype field is fetched for each attachment record so the
// badge and pencil can render reactively.
Many2ManyBinaryField.fieldsToFetch = {
    ...Many2ManyBinaryField.fieldsToFetch,
    document_type_id: {
        name: "document_type_id",
        type: "many2one",
        relation: "ir.attachment.document.type",
    },
};

patch(Many2ManyBinaryField.prototype, "web_attachment_classifier.Many2ManyBinaryField", {
    setup() {
        this._super(...arguments);
        this._classifierDialogService = useService("dialog");
        this._classifierOrm = useService("orm");
        this.classifierState = useState({
            options: [],
            isDraggingOver: false,
        });
        this._dragCounter = 0;
        onWillStart(async () => {
            const resModel = this.props.record.resModel;
            if (!resModel) {
                return;
            }
            // Search doctypes whose res_model_names include our resModel.
            // res_model_names is a stored comma-joined helper; ilike is
            // approximate but the JS filter below tightens it.
            const rows = await this._classifierOrm.searchRead(
                "ir.attachment.document.type",
                [["res_model_names", "ilike", resModel]],
                ["id", "name", "res_model_names"]
            );
            this.classifierState.options = rows.filter((r) =>
                (r.res_model_names || "").split(",").includes(resModel)
            );
        });
    },

    _hasFilesPayload(ev) {
        const types = ev.dataTransfer && ev.dataTransfer.types;
        if (!types) {
            return false;
        }
        return Array.from(types).includes("Files");
    },

    onDragEnter(ev) {
        if (this.props.readonly || !this._hasFilesPayload(ev)) {
            return;
        }
        this._dragCounter += 1;
        this.classifierState.isDraggingOver = true;
    },

    onDragOver(ev) {
        if (this.props.readonly || !this._hasFilesPayload(ev)) {
            return;
        }
        ev.dataTransfer.dropEffect = "copy";
    },

    onDragLeave() {
        if (this._dragCounter > 0) {
            this._dragCounter -= 1;
        }
        if (this._dragCounter === 0) {
            this.classifierState.isDraggingOver = false;
        }
    },

    async onDrop(ev) {
        this._dragCounter = 0;
        this.classifierState.isDraggingOver = false;
        if (this.props.readonly || !this._hasFilesPayload(ev)) {
            return;
        }
        const files = Array.from(ev.dataTransfer.files || []);
        if (!files.length) {
            return;
        }
        await this._uploadDroppedFiles(files);
    },

    async _uploadDroppedFiles(files) {
        const http = this.env.services.http;
        const notification = this.env.services.notification;
        const params = {
            csrf_token: odoo.csrf_token,
            ufile: files,
            model: this.props.record.resModel,
            id: this.props.record.data.id || 0,
        };
        let parsed;
        try {
            const raw = await http.post(
                "/web/binary/upload_attachment",
                params,
                "text"
            );
            parsed = JSON.parse(raw);
        } catch (error) {
            notification.add(error.message || String(error), {
                title: this.env._t("Uploading error"),
                type: "danger",
            });
            return;
        }
        const okIds = [];
        for (const att of parsed) {
            if (att.error) {
                notification.add(att.error, {
                    title: this.env._t("Uploading error"),
                    type: "danger",
                });
            } else {
                okIds.push(att.id);
            }
        }
        if (okIds.length) {
            await this.operations.saveRecord(okIds);
        }
    },

    onEditClick(fileId, currentValue) {
        this._classifierDialogService.add(AttachmentClassifierDialog, {
            options: this.classifierState.options,
            initialValue: currentValue == null ? "" : String(currentValue),
            onSave: async (newValue) => {
                await this._classifierOrm.write("ir.attachment", [fileId], {
                    document_type_id: newValue ? Number(newValue) : false,
                });
                await this.props.record.load();
            },
        });
    },
});
