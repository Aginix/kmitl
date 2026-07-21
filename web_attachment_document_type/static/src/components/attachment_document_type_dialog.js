/** @odoo-module **/

import {Dialog} from "@web/core/dialog/dialog";
import {Component, useRef, useState} from "@odoo/owl";

/**
 * Unified dialog for the attach + doctype flow.
 *
 * mode="edit" (default): a single dropdown to set document_type_id on
 *   an existing attachment. onSave({value}).
 *
 * mode="add": file input (multiple) + dropdown. onSave({files, value}).
 *   The file input accepts drag & drop; dropped files are pushed onto
 *   the underlying <input type="file"> via the DataTransfer API so the
 *   save path is uniform.
 */
export class AttachmentDocumentTypeDialog extends Component {
    setup() {
        this.notification = this.env.services.notification;
        this.state = useState({
            value: this.props.initialValue || "",
            isDraggingOver: false,
            saving: false,
        });
        this._dragCounter = 0;
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

    onValueChange(ev) {
        this.state.value = ev.target.value;
    }

    // Compares a raw option id (typically Number) against the currently
    // selected value stored as a String in state. Exposed on the
    // component so the template can call it without needing the global
    // `String` (OWL 1 templates run in a ctx scope that doesn't expose
    // JS globals).
    isSelected(rawValue) {
        const asString = rawValue == null ? "" : "" + rawValue;
        return asString === this.state.value;
    }

    // -----------------------------------------------------------------
    // Drag & drop on the file input area (add mode only)
    // -----------------------------------------------------------------
    _hasFilesPayload(ev) {
        const types = ev.dataTransfer && ev.dataTransfer.types;
        if (!types) {
            return false;
        }
        return Array.from(types).includes("Files");
    }

    _assignFilesToInput(files) {
        const input = this.fileInputRef.el;
        if (!input) {
            return;
        }
        const dt = new DataTransfer();
        for (const f of files) {
            dt.items.add(f);
        }
        input.files = dt.files;
    }

    onDragEnter(ev) {
        if (!this.isAddMode || !this._hasFilesPayload(ev)) {
            return;
        }
        this._dragCounter += 1;
        this.state.isDraggingOver = true;
    }

    onDragOver(ev) {
        if (!this.isAddMode || !this._hasFilesPayload(ev)) {
            return;
        }
        ev.dataTransfer.dropEffect = "copy";
    }

    onDragLeave() {
        if (this._dragCounter > 0) {
            this._dragCounter -= 1;
        }
        if (this._dragCounter === 0) {
            this.state.isDraggingOver = false;
        }
    }

    onDrop(ev) {
        this._dragCounter = 0;
        this.state.isDraggingOver = false;
        if (!this.isAddMode || !this._hasFilesPayload(ev)) {
            return;
        }
        const files = Array.from(ev.dataTransfer.files || []);
        if (files.length) {
            this._assignFilesToInput(files);
        }
    }

    // -----------------------------------------------------------------
    // Save / cancel
    // -----------------------------------------------------------------
    async onSave() {
        if (this.state.saving) {
            return;
        }
        if (this.isAddMode) {
            const fileInput = this.fileInputRef.el;
            const files = fileInput ? Array.from(fileInput.files) : [];
            if (!files.length) {
                this.notification.add(this.env._t("Please select a file."), {
                    type: "warning",
                });
                return;
            }
            this.state.saving = true;
            try {
                await this.props.onSave({files, value: this.state.value});
            } catch (error) {
                this.state.saving = false;
                throw error;
            }
        } else {
            this.state.saving = true;
            try {
                await this.props.onSave({value: this.state.value});
            } catch (error) {
                this.state.saving = false;
                throw error;
            }
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

AttachmentDocumentTypeDialog.template =
    "web_attachment_document_type.AttachmentDocumentTypeDialog";
AttachmentDocumentTypeDialog.components = {Dialog};
AttachmentDocumentTypeDialog.props = {
    mode: {type: String, optional: true},
    title: {type: String, optional: true},
    options: {type: Array},
    initialValue: {type: String, optional: true},
    onSave: {type: Function},
    close: {type: Function},
};
