/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {onWillStart, useState} from "@odoo/owl";
import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {AttachmentClassifierDialog} from "@web_attachment_classifier/components/attachment_classifier_dialog";

// Ensure the doctype field is fetched for each attachment record so the
// badge renders reactively.
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

    // ------------------------------------------------------------------
    // Attach flow — intercept the FileInput trigger so that when doctypes
    // exist for this res_model we open our dialog instead of the OS file
    // picker. Return `true` to fall through to the standard behaviour.
    // ------------------------------------------------------------------
    async beforeAttachClick() {
        if (!this.classifierState.options.length) {
            return true;
        }
        this._openAddDialog();
        return false;
    },

    _openAddDialog() {
        this._classifierDialogService.add(AttachmentClassifierDialog, {
            mode: "add",
            options: this.classifierState.options,
            onSave: async ({files, value}) => {
                await this._uploadAndLink(files, value ? Number(value) : false);
            },
        });
    },

    // Shared: POST files to /web/binary/upload_attachment, write the
    // classifier when supplied, and link the successful ids to the parent.
    async _uploadAndLink(files, doctypeId) {
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
        if (!okIds.length) {
            return;
        }
        if (doctypeId) {
            await this._classifierOrm.write("ir.attachment", okIds, {
                document_type_id: doctypeId,
            });
        }
        await this.operations.saveRecord(okIds);
    },

    // ------------------------------------------------------------------
    // Drag & drop — uploads immediately without asking for a doctype;
    // user can tag the newly-added attachments via the badge afterward.
    // ------------------------------------------------------------------
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
        await this._uploadAndLink(files, false);
    },

    // ------------------------------------------------------------------
    // Post-hoc edit: click the doctype badge to change (or set) it.
    // No pencil button — the badge itself is the affordance.
    // ------------------------------------------------------------------
    onBadgeClick(fileId, currentValue) {
        if (this.props.readonly || !this.classifierState.options.length) {
            return;
        }
        this._classifierDialogService.add(AttachmentClassifierDialog, {
            mode: "edit",
            options: this.classifierState.options,
            initialValue: currentValue == null ? "" : String(currentValue),
            onSave: async ({value}) => {
                await this._classifierOrm.write("ir.attachment", [fileId], {
                    document_type_id: value ? Number(value) : false,
                });
                // Reload the specific child record so its fieldsToFetch
                // (including document_type_id) re-fetches; a plain
                // props.record.load() on the parent doesn't propagate to
                // x2many children in Odoo 16.
                const target = this.props.value.records.find(
                    (r) => r.data.id === fileId
                );
                if (target) {
                    await target.load();
                } else {
                    await this.props.record.load();
                }
            },
        });
    },

    // Serve attachments inline (open in a new tab) instead of forcing a
    // download. Combined with the template patch that strips the HTML5
    // `download` attribute from the anchors, clicking a filename now
    // opens the file in the browser; right-click → Save link as… still
    // works for the download intent.
    getUrl(id) {
        return `/web/content/${id}?download=false`;
    },
});
