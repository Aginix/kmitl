/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {onWillStart, useState} from "@odoo/owl";
import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {AttachmentClassifierDialog} from "./attachment_classifier_dialog";

/**
 * Base class extending Many2ManyBinaryField with a single classifier field
 * (Many2one or Selection) stored on ir.attachment. Not meant to be
 * registered directly — use `registerAttachmentClassifierWidget` to create
 * and register a concrete subclass that binds a specific classifier field.
 */
export class Many2ManyBinaryClassifierField extends Many2ManyBinaryField {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.dragState = useState({isDraggingOver: false});
        this.dragCounter = 0;
        this.selectionMap = {};
        if (this.classifierType === "selection") {
            const selection = this.constructor.classifierSelection;
            if (selection) {
                this.selectionMap = Object.fromEntries(selection);
            } else {
                onWillStart(async () => {
                    const fieldsInfo = await this.orm.call(
                        "ir.attachment",
                        "fields_get",
                        [[this.classifierField], ["selection"]]
                    );
                    const sel =
                        (fieldsInfo[this.classifierField] || {}).selection || [];
                    this.selectionMap = Object.fromEntries(sel);
                });
            }
        }
    }

    get classifierField() {
        return this.constructor.classifierField;
    }

    get classifierLabel() {
        return this.constructor.classifierLabel;
    }

    get classifierType() {
        return this.constructor.classifierType;
    }

    get files() {
        const field = this.classifierField;
        return this.props.value.records.map((record) => {
            const raw = field ? record.data[field] : null;
            let classifierName = "";
            let classifierRawId = null;
            if (raw) {
                if (this.classifierType === "selection") {
                    classifierName = this.selectionMap[raw] || raw;
                    classifierRawId = raw;
                } else if (Array.isArray(raw)) {
                    // Many2one → [id, display_name]
                    classifierName = raw[1];
                    classifierRawId = raw[0];
                }
            }
            return {...record.data, classifierName, classifierRawId};
        });
    }

    _dialogProps() {
        return {
            resModel: this.props.record.resModel,
            resId: this.props.record.data.id || 0,
            classifierType: this.constructor.classifierType,
            classifierModel: this.constructor.classifierModel,
            classifierField: this.constructor.classifierField,
            classifierLabel: this.constructor.classifierLabel,
            classifierDomain: this.constructor.classifierDomain,
            classifierSelection: this.constructor.classifierSelection,
            classifierRequired: this.constructor.classifierRequired,
        };
    }

    onAddClick() {
        this._openAddDialog(null);
    }

    _openAddDialog(initialFiles) {
        this.dialog.add(AttachmentClassifierDialog, {
            ..._defaultsWithMode(this._dialogProps(), "add"),
            initialFiles: initialFiles || undefined,
            onConfirm: (attachmentIds) => this.operations.saveRecord(attachmentIds),
        });
    }

    _hasFilesPayload(ev) {
        const types = ev.dataTransfer && ev.dataTransfer.types;
        if (!types) {
            return false;
        }
        return Array.from(types).includes("Files");
    }

    onDragEnter(ev) {
        if (this.props.readonly || !this._hasFilesPayload(ev)) {
            return;
        }
        this.dragCounter += 1;
        this.dragState.isDraggingOver = true;
    }

    onDragOver(ev) {
        if (this.props.readonly || !this._hasFilesPayload(ev)) {
            return;
        }
        ev.dataTransfer.dropEffect = "copy";
    }

    onDragLeave() {
        if (this.dragCounter > 0) {
            this.dragCounter -= 1;
        }
        if (this.dragCounter === 0) {
            this.dragState.isDraggingOver = false;
        }
    }

    onDrop(ev) {
        this.dragCounter = 0;
        this.dragState.isDraggingOver = false;
        if (this.props.readonly || !this._hasFilesPayload(ev)) {
            return;
        }
        const files = Array.from(ev.dataTransfer.files || []);
        if (files.length) {
            this._openAddDialog(files);
        }
    }

    onEditClick(fileId, currentValue) {
        this.dialog.add(AttachmentClassifierDialog, {
            ..._defaultsWithMode(this._dialogProps(), "edit"),
            attachmentId: fileId,
            initialClassifierId: currentValue == null ? "" : String(currentValue),
            onConfirm: () => this.props.record.load(),
        });
    }
}

function _defaultsWithMode(base, mode) {
    return {...base, mode};
}

Many2ManyBinaryClassifierField.template =
    "web_attachment_classifier.Many2ManyBinaryClassifierField";
// Subclasses override these — declared here for documentation only.
Many2ManyBinaryClassifierField.classifierType = "many2one";
Many2ManyBinaryClassifierField.classifierField = null;
Many2ManyBinaryClassifierField.classifierModel = null;
Many2ManyBinaryClassifierField.classifierLabel = "";
Many2ManyBinaryClassifierField.classifierDomain = [];
Many2ManyBinaryClassifierField.classifierSelection = null;
Many2ManyBinaryClassifierField.classifierRequired = false;

/**
 * Register a widget that lets users upload attachments together with a
 * single classifier value stored on ir.attachment. Supports Many2one
 * (default) and Selection fields.
 *
 * @param {Object} config
 * @param {String} config.widgetName        Name used as widget="..." in views
 * @param {String} config.classifierField   Field name on ir.attachment
 * @param {String} config.classifierLabel   Label shown in the dialog + list
 * @param {String} [config.classifierType="many2one"] "many2one" or "selection"
 * @param {String} [config.classifierModel] Comodel — required for many2one
 * @param {Array}  [config.classifierDomain=[]] Domain filter — many2one only
 * @param {Array}  [config.classifierSelection] Selection tuples
 *                                              [[value,label],...] — optional
 *                                              for selection: if not provided
 *                                              the widget looks it up via
 *                                              fields_get at render time.
 * @param {Boolean} [config.classifierRequired=false] Force a value at upload
 *                                              and edit time.
 * @returns The registered subclass (useful for further extension in tests)
 */
export function registerAttachmentClassifierWidget({
    widgetName,
    classifierField,
    classifierLabel,
    classifierType = "many2one",
    classifierModel = null,
    classifierDomain = [],
    classifierSelection = null,
    classifierRequired = false,
}) {
    class ConcreteAttachmentClassifierField extends Many2ManyBinaryClassifierField {}
    ConcreteAttachmentClassifierField.classifierType = classifierType;
    ConcreteAttachmentClassifierField.classifierField = classifierField;
    ConcreteAttachmentClassifierField.classifierModel = classifierModel;
    ConcreteAttachmentClassifierField.classifierLabel = classifierLabel;
    ConcreteAttachmentClassifierField.classifierDomain = classifierDomain;
    ConcreteAttachmentClassifierField.classifierSelection = classifierSelection;
    ConcreteAttachmentClassifierField.classifierRequired = classifierRequired;
    // fieldsToFetch is a static per-class contract used by the framework to
    // decide which fields of child records to load. It cannot be dynamic per
    // instance, so we bake it into the subclass here.
    const fieldDescriptor =
        classifierType === "selection"
            ? {
                  name: classifierField,
                  type: "selection",
                  selection: classifierSelection || [],
              }
            : {name: classifierField, type: "many2one", relation: classifierModel};
    ConcreteAttachmentClassifierField.fieldsToFetch = {
        ...Many2ManyBinaryField.fieldsToFetch,
        [classifierField]: fieldDescriptor,
    };
    registry.category("fields").add(widgetName, ConcreteAttachmentClassifierField);
    return ConcreteAttachmentClassifierField;
}
