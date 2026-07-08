/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, onWillStart, useRef, useState } from "@odoo/owl";

export class AttachmentDocTypeDialog extends Component {
    setup() {
        // Use the raw services (not useService) so the upload/write still
        // complete even if this dialog is destroyed mid-save (e.g. the form
        // reloads after the first attachment on a fresh record).
        this.orm = this.env.services.orm;
        this.http = this.env.services.http;
        this.notification = this.env.services.notification;
        this.fileInputRef = useRef("fileInput");
        this.state = useState({ documentTypeId: "" });
        this.docTypes = [];
        onWillStart(async () => {
            this.docTypes = await this.orm.searchRead(
                "kris.project.document.type",
                [],
                ["id", "name"]
            );
        });
    }

    async onSave() {
        const fileInput = this.fileInputRef.el;
        const file = fileInput && fileInput.files[0];
        if (!file) {
            this.notification.add(this.env._t("Please select a file."), {
                type: "warning",
            });
            return;
        }
        const params = {
            csrf_token: odoo.csrf_token,
            ufile: [file],
            model: this.props.resModel,
            id: this.props.resId,
        };
        let result;
        try {
            result = JSON.parse(
                await this.http.post("/web/binary/upload_attachment", params, "text")
            );
        } catch (error) {
            this.notification.add(error.message || String(error), {
                title: this.env._t("Uploading error"),
                type: "danger",
            });
            return;
        }
        const attachment = result[0];
        if (attachment.error) {
            this.notification.add(attachment.error, {
                title: this.env._t("Uploading error"),
                type: "danger",
            });
            return;
        }
        if (this.state.documentTypeId) {
            await this.orm.write("ir.attachment", [attachment.id], {
                document_type_id: Number(this.state.documentTypeId),
            });
        }
        await this.props.onConfirm(attachment.id);
        try {
            this.props.close();
        } catch (e) {
            // dialog may already be closed if the form reloaded
        }
    }
}

AttachmentDocTypeDialog.template = "kris_project.AttachmentDocTypeDialog";
AttachmentDocTypeDialog.components = { Dialog };
AttachmentDocTypeDialog.props = {
    resModel: { type: String },
    resId: { type: Number },
    onConfirm: { type: Function },
    close: { type: Function },
};
