/** @odoo-module **/

import {Domain} from "@web/core/domain";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";
import {registry} from "@web/core/registry";

// A Many2one dropdown over a Many2oneReference: the cited document of a
// related.document row. The generic ``reference`` widget cannot be used, it
// reads ir.model, which regular users may not. The model comes from the row's
// target_res_model and the domain from picker_domain, both set by its kind.
export class RelatedDocumentPickerField extends Many2OneField {
    setup() {
        super.setup();
        this.update = (value) => {
            this.state.isFloating = false;
            return this.props.update(value ? value[0].id : false);
        };
    }

    get relation() {
        return this.props.record.data.target_res_model;
    }

    get resId() {
        return this.props.value;
    }

    // The snapshot, which still reads when the target is gone or unreadable.
    get displayName() {
        const data = this.props.record.data;
        return this.props.value ? data.document_number || data.name || "" : "";
    }

    get extraLines() {
        return [];
    }

    getDomain() {
        const raw = this.props.record.data.picker_domain || "[]";
        return new Domain(raw).toList(this.context);
    }
}
RelatedDocumentPickerField.supportedTypes = ["many2one_reference"];
RelatedDocumentPickerField.extractProps = (params) => ({
    ...Many2OneField.extractProps(params),
    // Opening is the row's own button: it opens as the reader.
    canOpen: false,
    canCreate: false,
    canQuickCreate: false,
    canCreateEdit: false,
});

registry.category("fields").add("related_document_picker", RelatedDocumentPickerField);
