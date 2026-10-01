/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";
import { AttachmentCarouselDialog } from "./attachment_carousel_dialog";

// Opt-in via `options="{'carousel': 1}"` on the field — chosen over a
// standalone widget so Many2ManyBinaryField patches from other modules
// (notably web_attachment_document_type: badges, drag/drop, FileInput
// beforeOpen) keep working on the same field.
Many2ManyBinaryField.props = {
    ...Many2ManyBinaryField.props,
    carousel: { type: Boolean, optional: true },
};

patch(Many2ManyBinaryField, "attachment_carousel.static", {
    extractProps({ attrs, field }) {
        const base = this._super({ attrs, field });
        return {
            ...base,
            carousel: !!(attrs.options && attrs.options.carousel),
        };
    },
});

patch(
    Many2ManyBinaryField.prototype,
    "attachment_carousel.Many2ManyBinaryField",
    {
        setup() {
            this._super(...arguments);
            this._carouselDialogService = useService("dialog");
        },

        // Neutralise the chip's inner <a href=getUrl(id)> when carousel is on
        // so clicking a filename doesn't race the wrap-level click handler
        // (download/open-in-tab would fire before our dialog opens).
        getUrl(id) {
            if (this.props.carousel) {
                return "#";
            }
            return this._super(id);
        },

        onCarouselClick(ev, index) {
            if (!this.props.carousel) {
                return;
            }
            // Let sibling patches own their own click targets:
            // - delete button (.o_attachment_delete) already stops propagation
            // - doctype badge (web_attachment_document_type) does not, so bail
            //   out here when the click originated inside it
            if (
                ev.target.closest(".o_attachment_doctype_badge_clickable") ||
                ev.target.closest(".o_attachment_delete")
            ) {
                return;
            }
            ev.preventDefault();
            if (!this.files.length) {
                return;
            }
            this._carouselDialogService.add(AttachmentCarouselDialog, {
                attachments: this.files,
                startIndex: index,
                title: this.props.uploadText || this.env._t("Attachments"),
            });
        },
    }
);
