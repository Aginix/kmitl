/** @odoo-module **/

import {Dialog} from "@web/core/dialog/dialog";
import {Component, useRef, useState} from "@odoo/owl";

/**
 * Unified dialog for the classifier flow.
 *
 * mode="edit" (default): a single dropdown to set document_type_id on
 *   an existing attachment. onSave({value}).
 *
 * mode="add": file input (multiple) + dropdown. onSave({files, value}).
 *   Caller uploads and links.
 */
export class AttachmentClassifierDialog extends Component {
    setup() {
        this.notification = this.env.services.notification;
        this.state = useState({
            value: this.props.initialValue || "",
        });
        this.fileInputRef = useRef("fileInput");
    }

    get isAddMode() {
        return this.props.mode === "add";
    }

    get title() {
        return (
            this.props.title ||
            (this.isAddMode
                ? this.env._t("Add Attachment")
                : this.env._t("Document Type"))
        );
    }

    async onSave() {
        if (this.isAddMode) {
            const fileInput = this.fileInputRef.el;
            const files = fileInput ? Array.from(fileInput.files) : [];
            if (!files.length) {
                this.notification.add(this.env._t("Please select a file."), {
                    type: "warning",
                });
                return;
            }
            await this.props.onSave({files, value: this.state.value});
        } else {
            await this.props.onSave({value: this.state.value});
        }
        this._safeClose();
    }

    onCancel() {
        this._safeClose();
    }

    _safeClose() {
        try {
            this.props.close();
        } catch (e) {
            // dialog may already be closed if the form reloaded
        }
    }
}

AttachmentClassifierDialog.template =
    "web_attachment_classifier.AttachmentClassifierDialog";
AttachmentClassifierDialog.components = {Dialog};
AttachmentClassifierDialog.props = {
    mode: {type: String, optional: true},
    title: {type: String, optional: true},
    options: {type: Array},
    initialValue: {type: String, optional: true},
    onSave: {type: Function},
    close: {type: Function},
};
