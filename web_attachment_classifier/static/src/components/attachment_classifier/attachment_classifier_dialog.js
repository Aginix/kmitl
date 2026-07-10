/** @odoo-module **/

import {Dialog} from "@web/core/dialog/dialog";
import {Component, onWillStart, useRef, useState} from "@odoo/owl";

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
        });
        this.classifierOptions = [];
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
        await this.orm.write("ir.attachment", [this.props.attachmentId], {
            [this.props.classifierField]: this._castValue(this.state.classifierId),
        });
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
    mode: {type: String, optional: true},
    attachmentId: {type: Number, optional: true},
    initialClassifierId: {type: String, optional: true},
    onConfirm: {type: Function},
    close: {type: Function},
};
