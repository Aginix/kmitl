/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {onWillStart} from "@odoo/owl";
import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {AttachmentMetadataDialog} from "./attachment_metadata_dialog";

/**
 * Base class extending Many2ManyBinaryField with a single metadata field
 * (Many2one or Selection) stored on ir.attachment. Not meant to be
 * registered directly — use `registerAttachmentMetadataWidget` to create and
 * register a concrete subclass that binds a specific metadata field.
 */
export class Many2ManyBinaryMetadataField extends Many2ManyBinaryField {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.selectionMap = {};
        if (this.metadataType === "selection") {
            const selection = this.constructor.metadataSelection;
            if (selection) {
                this.selectionMap = Object.fromEntries(selection);
            } else {
                onWillStart(async () => {
                    const fieldsInfo = await this.orm.call(
                        "ir.attachment",
                        "fields_get",
                        [[this.metadataField], ["selection"]]
                    );
                    const sel =
                        (fieldsInfo[this.metadataField] || {}).selection || [];
                    this.selectionMap = Object.fromEntries(sel);
                });
            }
        }
    }

    get metadataField() {
        return this.constructor.metadataField;
    }

    get metadataLabel() {
        return this.constructor.metadataLabel;
    }

    get metadataType() {
        return this.constructor.metadataType;
    }

    get files() {
        const field = this.metadataField;
        return this.props.value.records.map((record) => {
            const raw = field ? record.data[field] : null;
            let metadataName = "";
            if (raw) {
                if (this.metadataType === "selection") {
                    metadataName = this.selectionMap[raw] || raw;
                } else {
                    // Many2one → [id, display_name]
                    metadataName = Array.isArray(raw) ? raw[1] : "";
                }
            }
            return {...record.data, metadataName};
        });
    }

    onAddClick() {
        this.dialog.add(AttachmentMetadataDialog, {
            resModel: this.props.record.resModel,
            resId: this.props.record.data.id || 0,
            metadataType: this.constructor.metadataType,
            metadataModel: this.constructor.metadataModel,
            metadataField: this.constructor.metadataField,
            metadataLabel: this.constructor.metadataLabel,
            metadataDomain: this.constructor.metadataDomain,
            metadataSelection: this.constructor.metadataSelection,
            onConfirm: (attachmentId) => this.operations.saveRecord([attachmentId]),
        });
    }
}

Many2ManyBinaryMetadataField.template =
    "web_attachment_metadata.Many2ManyBinaryMetadataField";
// Subclasses override these — declared here for documentation only.
Many2ManyBinaryMetadataField.metadataType = "many2one";
Many2ManyBinaryMetadataField.metadataField = null;
Many2ManyBinaryMetadataField.metadataModel = null;
Many2ManyBinaryMetadataField.metadataLabel = "";
Many2ManyBinaryMetadataField.metadataDomain = [];
Many2ManyBinaryMetadataField.metadataSelection = null;

/**
 * Register a widget that lets users upload an attachment together with a
 * single metadata value stored on ir.attachment. Supports Many2one (default)
 * and Selection fields.
 *
 * @param {Object} config
 * @param {String} config.widgetName        Name used as widget="..." in views
 * @param {String} config.metadataField     Field name on ir.attachment
 * @param {String} config.metadataLabel     Label shown in the dialog + list
 * @param {String} [config.metadataType="many2one"] "many2one" or "selection"
 * @param {String} [config.metadataModel]   Comodel — required for many2one
 * @param {Array}  [config.metadataDomain=[]] Domain filter — many2one only
 * @param {Array}  [config.metadataSelection] Selection tuples [[value,label],...]
 *                                           — optional for selection: if not
 *                                           provided the widget looks it up via
 *                                           fields_get at render time
 * @returns The registered subclass (useful for further extension in tests)
 */
export function registerAttachmentMetadataWidget({
    widgetName,
    metadataField,
    metadataLabel,
    metadataType = "many2one",
    metadataModel = null,
    metadataDomain = [],
    metadataSelection = null,
}) {
    class ConcreteAttachmentMetadataField extends Many2ManyBinaryMetadataField {}
    ConcreteAttachmentMetadataField.metadataType = metadataType;
    ConcreteAttachmentMetadataField.metadataField = metadataField;
    ConcreteAttachmentMetadataField.metadataModel = metadataModel;
    ConcreteAttachmentMetadataField.metadataLabel = metadataLabel;
    ConcreteAttachmentMetadataField.metadataDomain = metadataDomain;
    ConcreteAttachmentMetadataField.metadataSelection = metadataSelection;
    // fieldsToFetch is a static per-class contract used by the framework to
    // decide which fields of child records to load. It cannot be dynamic per
    // instance, so we bake it into the subclass here.
    const fieldDescriptor =
        metadataType === "selection"
            ? {
                  name: metadataField,
                  type: "selection",
                  selection: metadataSelection || [],
              }
            : {name: metadataField, type: "many2one", relation: metadataModel};
    ConcreteAttachmentMetadataField.fieldsToFetch = {
        ...Many2ManyBinaryField.fieldsToFetch,
        [metadataField]: fieldDescriptor,
    };
    registry.category("fields").add(widgetName, ConcreteAttachmentMetadataField);
    return ConcreteAttachmentMetadataField;
}
