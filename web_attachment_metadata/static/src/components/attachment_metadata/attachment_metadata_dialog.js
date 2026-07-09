/** @odoo-module **/

import {Dialog} from "@web/core/dialog/dialog";
import {Component, onWillStart, useRef, useState} from "@odoo/owl";

export class AttachmentMetadataDialog extends Component {
    setup() {
        // Use the raw services (not useService) so the upload/write still
        // complete even if this dialog is destroyed mid-save (e.g. the form
        // reloads after the first attachment on a fresh record).
        this.orm = this.env.services.orm;
        this.http = this.env.services.http;
        this.notification = this.env.services.notification;
        this.fileInputRef = useRef("fileInput");
        this.state = useState({metadataId: ""});
        this.metadataOptions = [];
        onWillStart(async () => {
            this.metadataOptions = await this.orm.searchRead(
                this.props.metadataModel,
                this.props.metadataDomain || [],
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
        if (this.state.metadataId) {
            await this.orm.write("ir.attachment", [attachment.id], {
                [this.props.metadataField]: Number(this.state.metadataId),
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

AttachmentMetadataDialog.template = "web_attachment_metadata.AttachmentMetadataDialog";
AttachmentMetadataDialog.components = {Dialog};
AttachmentMetadataDialog.props = {
    resModel: {type: String},
    resId: {type: Number},
    metadataModel: {type: String},
    metadataField: {type: String},
    metadataLabel: {type: String},
    metadataDomain: {type: Array, optional: true},
    onConfirm: {type: Function},
    close: {type: Function},
};
