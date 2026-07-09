/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {AttachmentMetadataDialog} from "./attachment_metadata_dialog";

/**
 * Base class extending Many2ManyBinaryField with a single Many2one metadata
 * field stored on ir.attachment. Not meant to be registered directly — use
 * `registerAttachmentMetadataWidget` to create and register a concrete
 * subclass that binds a specific metadata model + field.
 */
export class Many2ManyBinaryMetadataField extends Many2ManyBinaryField {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    get metadataField() {
        return this.constructor.metadataField;
    }

    get metadataLabel() {
        return this.constructor.metadataLabel;
    }

    get files() {
        const field = this.metadataField;
        return this.props.value.records.map((record) => ({
            ...record.data,
            metadataName: field && record.data[field] ? record.data[field][1] : "",
        }));
    }

    onAddClick() {
        this.dialog.add(AttachmentMetadataDialog, {
            resModel: this.props.record.resModel,
            resId: this.props.record.data.id || 0,
            metadataModel: this.constructor.metadataModel,
            metadataField: this.constructor.metadataField,
            metadataLabel: this.constructor.metadataLabel,
            metadataDomain: this.constructor.metadataDomain,
            onConfirm: (attachmentId) => this.operations.saveRecord([attachmentId]),
        });
    }
}

Many2ManyBinaryMetadataField.template =
    "web_attachment_metadata.Many2ManyBinaryMetadataField";
// Subclasses override these — declared here for documentation only.
Many2ManyBinaryMetadataField.metadataField = null;
Many2ManyBinaryMetadataField.metadataModel = null;
Many2ManyBinaryMetadataField.metadataLabel = "";
Many2ManyBinaryMetadataField.metadataDomain = [];

/**
 * Register a widget that lets users upload an attachment together with a
 * single Many2one metadata value stored on ir.attachment.
 *
 * @param {Object} config
 * @param {String} config.widgetName    Name used as widget="..." in views
 * @param {String} config.metadataField Field on ir.attachment (Many2one)
 * @param {String} config.metadataModel Comodel of that Many2one
 * @param {String} config.metadataLabel Label shown in the dialog + list
 * @param {Array}  [config.metadataDomain=[]] Domain used to filter options
 * @returns The registered subclass (useful for further extension in tests)
 */
export function registerAttachmentMetadataWidget({
    widgetName,
    metadataField,
    metadataModel,
    metadataLabel,
    metadataDomain = [],
}) {
    class ConcreteAttachmentMetadataField extends Many2ManyBinaryMetadataField {}
    ConcreteAttachmentMetadataField.metadataField = metadataField;
    ConcreteAttachmentMetadataField.metadataModel = metadataModel;
    ConcreteAttachmentMetadataField.metadataLabel = metadataLabel;
    ConcreteAttachmentMetadataField.metadataDomain = metadataDomain;
    // fieldsToFetch is a static per-class contract used by the framework to
    // decide which fields of child records to load. It cannot be dynamic per
    // instance, so we bake it into the subclass here.
    ConcreteAttachmentMetadataField.fieldsToFetch = {
        ...Many2ManyBinaryField.fieldsToFetch,
        [metadataField]: {
            name: metadataField,
            type: "many2one",
            relation: metadataModel,
        },
    };
    registry.category("fields").add(widgetName, ConcreteAttachmentMetadataField);
    return ConcreteAttachmentMetadataField;
}
