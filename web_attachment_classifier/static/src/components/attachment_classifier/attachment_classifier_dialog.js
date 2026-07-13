/** @odoo-module **/

import {Dialog} from "@web/core/dialog/dialog";
import {Component, onMounted, onWillStart, useRef, useState} from "@odoo/owl";

export class AttachmentClassifierDialog extends Component {
    setup() {
        // Use the raw services (not useService) so the upload/write still
        // complete even if this dialog is destroyed mid-save (e.g. the form
        // reloads after the first attachment on a fresh record).
        this.orm = this.env.services.orm;
        this.http = this.env.services.http;
        this.notification = this.env.services.notification;
        this.fileInputRef = useRef("fileInput");
        this.state = useState({
            classifierId: this.props.initialClassifierId || "",
            isDraggingOver: false,
        });
        this.dragCounter = 0;
        this.classifierOptions = [];
        onMounted(() => {
            if (this.props.initialFiles && this.props.initialFiles.length) {
                this._assignFilesToInput(this.props.initialFiles);
            }
        });
        onWillStart(async () => {
            if (this.props.classifierType === "selection") {
                if (this.props.classifierSelection) {
                    this.classifierOptions = this.props.classifierSelection.map(
                        ([value, label]) => ({id: value, name: label})
                    );
                } else {
                    const fieldsInfo = await this.orm.call(
                        "ir.attachment",
                        "fields_get",
                        [[this.props.classifierField], ["selection"]]
                    );
                    const selection =
                        (fieldsInfo[this.props.classifierField] || {}).selection || [];
                    this.classifierOptions = selection.map(([value, label]) => ({
                        id: value,
                        name: label,
                    }));
                }
            } else {
                this.classifierOptions = await this.orm.searchRead(
                    this.props.classifierModel,
                    this.props.classifierDomain || [],
                    ["id", "name"]
                );
            }
        });
    }

    get isEditMode() {
        return this.props.mode === "edit";
    }

    get title() {
        return this.isEditMode
            ? this.env._t("Edit ") + this.props.classifierLabel
            : this.env._t("Add Attachment");
    }

    _castValue(rawId) {
        if (!rawId) {
            return false;
        }
        return this.props.classifierType === "selection" ? rawId : Number(rawId);
    }

    _warnMissingClassifier() {
        this.notification.add(
            this.env._t("Please select ") + this.props.classifierLabel + ".",
            {type: "warning"}
        );
    }

    _assignFilesToInput(files) {
        const input = this.fileInputRef.el;
        if (!input) {
            return;
        }
        const list = this.isEditMode ? files.slice(0, 1) : files;
        const dt = new DataTransfer();
        list.forEach((f) => dt.items.add(f));
        input.files = dt.files;
    }

    _hasFilesPayload(ev) {
        const types = ev.dataTransfer && ev.dataTransfer.types;
        if (!types) {
            return false;
        }
        return Array.from(types).includes("Files");
    }

    onDragEnter(ev) {
        if (!this._hasFilesPayload(ev)) {
            return;
        }
        this.dragCounter += 1;
        this.state.isDraggingOver = true;
    }

    onDragOver(ev) {
        if (!this._hasFilesPayload(ev)) {
            return;
        }
        ev.dataTransfer.dropEffect = "copy";
    }

    onDragLeave() {
        if (this.dragCounter > 0) {
            this.dragCounter -= 1;
        }
        if (this.dragCounter === 0) {
            this.state.isDraggingOver = false;
        }
    }

    onDrop(ev) {
        this.dragCounter = 0;
        this.state.isDraggingOver = false;
        if (!this._hasFilesPayload(ev)) {
            return;
        }
        const files = Array.from(ev.dataTransfer.files || []);
        if (!files.length) {
            return;
        }
        if (this.isEditMode && files.length > 1) {
            this.notification.add(
                this.env._t(
                    "Only one file can replace the current attachment; keeping the first."
                ),
                {type: "warning"}
            );
        }
        this._assignFilesToInput(files);
    }

    _readAsBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const result = reader.result || "";
                const commaIdx = result.indexOf(",");
                resolve(commaIdx >= 0 ? result.slice(commaIdx + 1) : result);
            };
            reader.onerror = () => reject(reader.error || new Error("read failed"));
            reader.readAsDataURL(file);
        });
    }

    async _uploadOne(file) {
        const params = {
            csrf_token: odoo.csrf_token,
            ufile: [file],
            model: this.props.resModel,
            id: this.props.resId,
        };
        const response = await this.http.post(
            "/web/binary/upload_attachment",
            params,
            "text"
        );
        const attachment = JSON.parse(response)[0];
        if (attachment.error) {
            throw new Error(attachment.error);
        }
        if (this.state.classifierId) {
            await this.orm.write("ir.attachment", [attachment.id], {
                [this.props.classifierField]: this._castValue(this.state.classifierId),
            });
        }
        return attachment.id;
    }

    async _saveEdit() {
        if (this.props.classifierRequired && !this.state.classifierId) {
            this._warnMissingClassifier();
            return;
        }
        const fileInput = this.fileInputRef.el;
        const file = fileInput && fileInput.files[0];
        const writeVals = {
            [this.props.classifierField]: this._castValue(this.state.classifierId),
        };
        if (file) {
            try {
                writeVals.datas = await this._readAsBase64(file);
                writeVals.name = file.name;
                writeVals.mimetype = file.type || "application/octet-stream";
            } catch (error) {
                this.notification.add(
                    (file.name || "") + ": " + (error.message || String(error)),
                    {title: this.env._t("Read error"), type: "danger"}
                );
                return;
            }
        }
        try {
            await this.orm.write(
                "ir.attachment",
                [this.props.attachmentId],
                writeVals
            );
        } catch (error) {
            this.notification.add(error.message || String(error), {
                title: this.env._t("Save error"),
                type: "danger",
            });
            return;
        }
        await this.props.onConfirm();
        this._safeClose();
    }

    async _saveAdd() {
        const fileInput = this.fileInputRef.el;
        const files = fileInput ? Array.from(fileInput.files) : [];
        if (!files.length) {
            this.notification.add(this.env._t("Please select a file."), {
                type: "warning",
            });
            return;
        }
        if (this.props.classifierRequired && !this.state.classifierId) {
            this._warnMissingClassifier();
            return;
        }
        const successIds = [];
        for (const file of files) {
            try {
                const id = await this._uploadOne(file);
                successIds.push(id);
            } catch (error) {
                this.notification.add(
                    (file.name || "") + ": " + (error.message || String(error)),
                    {
                        title: this.env._t("Uploading error"),
                        type: "danger",
                    }
                );
            }
        }
        if (successIds.length) {
            await this.props.onConfirm(successIds);
        }
        this._safeClose();
    }

    _safeClose() {
        try {
            this.props.close();
        } catch (e) {
            // dialog may already be closed if the form reloaded
        }
    }

    onSave() {
        return this.isEditMode ? this._saveEdit() : this._saveAdd();
    }
}

AttachmentClassifierDialog.template =
    "web_attachment_classifier.AttachmentClassifierDialog";
AttachmentClassifierDialog.components = {Dialog};
AttachmentClassifierDialog.props = {
    resModel: {type: String},
    resId: {type: Number},
    classifierField: {type: String},
    classifierLabel: {type: String},
    classifierType: {type: String, optional: true},
    classifierModel: {type: String, optional: true},
    classifierDomain: {type: Array, optional: true},
    classifierSelection: {type: Array, optional: true},
    classifierRequired: {type: Boolean, optional: true},
    // "add" (default) uploads new attachment(s) via /web/binary/upload_attachment.
    // "edit" writes to an existing ir.attachment via ORM — required prop: attachmentId.
    mode: {type: String, optional: true},
    attachmentId: {type: Number, optional: true},
    initialClassifierId: {type: String, optional: true},
    initialFiles: {type: Array, optional: true},
    onConfirm: {type: Function},
    close: {type: Function},
};
