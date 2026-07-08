/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useRef, useState } from "@odoo/owl";

export class AttachmentDocTypeDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.http = useService("http");
        this.notification = useService("notification");
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
        const file = this.fileInputRef.el.files[0];
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
        const result = JSON.parse(
            await this.http.post("/web/binary/upload_attachment", params, "text")
        );
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
        this.props.close();
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
