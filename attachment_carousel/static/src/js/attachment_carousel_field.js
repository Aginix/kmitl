/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";
import { AttachmentCarouselDialog } from "./attachment_carousel_dialog";

export class AttachmentCarouselField extends Many2ManyBinaryField {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    onFileClick(index) {
        if (!this.files.length) {
            return;
        }
        this.dialog.add(AttachmentCarouselDialog, {
            attachments: this.files,
            startIndex: index,
            title: this.props.uploadText || this.env._t("Attachments"),
        });
    }
}

AttachmentCarouselField.template = "attachment_carousel.Field";
// Accept both m2m and o2m so the widget can drop-in on either shape of
// attachment_ids without an unsupported-field-type warning.
AttachmentCarouselField.supportedTypes = ["many2many", "one2many"];

registry.category("fields").add("attachment_carousel", AttachmentCarouselField);
