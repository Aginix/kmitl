/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {onWillStart, useState} from "@odoo/owl";
import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {AttachmentDocumentTypeDialog} from "@web_attachment_document_type/components/attachment_document_type_dialog";

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

patch(
    Many2ManyBinaryField.prototype,
    "web_attachment_document_type.Many2ManyBinaryField",
    {
        setup() {
            this._super(...arguments);
            this._doctypeDialogService = useService("dialog");
            this._doctypeOrm = useService("orm");
            this.doctypeState = useState({
                options: [],
                isDraggingOver: false,
                uploading: false,
            });
            this._dragCounter = 0;
            onWillStart(async () => {
                const resModel = this.props.record.resModel;
                if (!resModel) {
                    return;
                }
                // Query the per-model mapping table directly — filtered by
                // exact `res_model_name` and ordered by `sequence` — instead
                // of scanning all doctypes with an ilike + JS post-filter.
                const rels = await this._doctypeOrm.searchRead(
                    "ir.attachment.document.type.rel",
                    [["res_model_name", "=", resModel]],
                    ["document_type_id"],
                    {order: "sequence, id"}
                );
                this.doctypeState.options = rels
                    .filter((r) => r.document_type_id)
                    .map((r) => ({
                        id: r.document_type_id[0],
                        name: r.document_type_id[1],
                    }));
            });
        },

        // ------------------------------------------------------------------
        // Attach flow — intercept the FileInput trigger so that when doctypes
        // exist for this res_model we open our dialog instead of the OS file
        // picker. Return `true` to fall through to the standard behaviour.
        // ------------------------------------------------------------------
        async beforeAttachClick() {
            if (!this.doctypeState.options.length) {
                return true;
            }
            this._openAddDialog();
            return false;
        },

        _openAddDialog() {
            this._doctypeDialogService.add(AttachmentDocumentTypeDialog, {
                mode: "add",
                options: this.doctypeState.options,
                onSave: async ({files, value}) => {
                    await this._uploadAndLink(files, value ? Number(value) : false);
                },
            });
        },

        // Shared: POST files to /web/binary/upload_attachment, write the
        // doctype when supplied, and link the successful ids to the parent.
        // Toggles `doctypeState.uploading` so the widget can render an
        // overlay + spinner, and drops a success toast once the ids are
        // linked so the user has a positive confirmation instead of
        // wondering whether to click Attach again.
        async _uploadAndLink(files, doctypeId) {
            const http = this.env.services.http;
            const notification = this.env.services.notification;
            this.doctypeState.uploading = true;
            try {
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
                    await this._doctypeOrm.write("ir.attachment", okIds, {
                        document_type_id: doctypeId,
                    });
                }
                await this.operations.saveRecord(okIds);
                notification.add(this.env._t("Attachment(s) added"), {
                    type: "success",
                });
            } finally {
                this.doctypeState.uploading = false;
            }
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
            this.doctypeState.isDraggingOver = true;
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
                this.doctypeState.isDraggingOver = false;
            }
        },

        async onDrop(ev) {
            this._dragCounter = 0;
            this.doctypeState.isDraggingOver = false;
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
            if (this.props.readonly || !this.doctypeState.options.length) {
                return;
            }
            this._doctypeDialogService.add(AttachmentDocumentTypeDialog, {
                mode: "edit",
                options: this.doctypeState.options,
                initialValue: currentValue == null ? "" : String(currentValue),
                onSave: async ({value}) => {
                    await this._doctypeOrm.write("ir.attachment", [fileId], {
                        document_type_id: value ? Number(value) : false,
                    });
                    // Re-fetch the child attachment record so its
                    // fieldsToFetch (badge) picks up the new value, then
                    // re-fetch the root form so the chatter shows the
                    // tracking message posted server-side by
                    // ir.attachment.write.
                    const target = this.props.value.records.find(
                        (r) => r.data.id === fileId
                    );
                    if (target) {
                        await target.load();
                    }
                    await this.props.record.load();
                    // Odoo 16's Record.load() does not fire model.notify()
                    // at the end, so OWL doesn't know the data has moved —
                    // components watching these records stay stale until a
                    // full page reload. Kick the reactivity system manually.
                    this.props.record.model.notify();
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
    }
);
