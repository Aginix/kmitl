/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";
import { AttachmentDocTypeDialog } from "./attachment_doctype_dialog";

export class Many2ManyBinaryDocTypeField extends Many2ManyBinaryField {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    get files() {
        return this.props.value.records.map((record) => ({
            ...record.data,
            documentTypeName: record.data.document_type_id
                ? record.data.document_type_id[1]
                : "",
        }));
    }

    onAddClick() {
        this.dialog.add(AttachmentDocTypeDialog, {
            resModel: this.props.record.resModel,
            resId: this.props.record.data.id || 0,
            onConfirm: (attachmentId) => this.operations.saveRecord([attachmentId]),
        });
    }
}

Many2ManyBinaryDocTypeField.template = "kris_project.Many2ManyBinaryDocTypeField";
Many2ManyBinaryDocTypeField.components = {};
Many2ManyBinaryDocTypeField.fieldsToFetch = {
    name: { type: "char" },
    mimetype: { type: "char" },
    document_type_id: {
        name: "document_type_id",
        type: "many2one",
        relation: "kris.project.document.type",
    },
};

registry.category("fields").add("many2many_binary_doctype", Many2ManyBinaryDocTypeField);
