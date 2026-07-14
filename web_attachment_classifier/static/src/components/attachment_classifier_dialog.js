/** @odoo-module **/

import {Dialog} from "@web/core/dialog/dialog";
import {Component, useState} from "@odoo/owl";

/**
 * Small edit dialog: a single dropdown to set the document_type_id on
 * one or more existing ir.attachment records. Save is optional — Skip
 * closes the dialog without writing anything.
 */
export class AttachmentClassifierDialog extends Component {
    setup() {
        this.state = useState({
            value: this.props.initialValue || "",
        });
    }

    async onSave() {
        await this.props.onSave(this.state.value);
        this._safeClose();
    }

    onSkip() {
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
    title: {type: String, optional: true},
    options: {type: Array},
    initialValue: {type: String, optional: true},
    onSave: {type: Function},
    close: {type: Function},
};
