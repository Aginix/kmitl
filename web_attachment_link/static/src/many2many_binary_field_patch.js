/** @odoo-module **/

import {AttachmentLinkDialog} from "@web_attachment_link/attachment_link_dialog";
import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

Many2ManyBinaryField.fieldsToFetch = {
    ...Many2ManyBinaryField.fieldsToFetch,
    type: {type: "selection"},
    url: {type: "char"},
};

Many2ManyBinaryField.props = {
    ...Many2ManyBinaryField.props,
    noLink: {type: Boolean, optional: true},
};

const extractProps = Many2ManyBinaryField.extractProps;
Many2ManyBinaryField.extractProps = (params) => ({
    ...extractProps(params),
    noLink: Boolean(params.attrs.options.no_link),
});

patch(Many2ManyBinaryField.prototype, "web_attachment_link.Many2ManyBinaryField", {
    setup() {
        this._super(...arguments);
        this.linkDialog = useService("dialog");
    },

    /**
     * A field restricted to some file extensions expects files, not links.
     * A method, not a getter: OWL copies a patched (enumerable) getter into
     * the FileInput slot scope and fails.
     */
    canAttachLink() {
        return !(
            this.props.readonly ||
            this.props.acceptedFileExtensions ||
            this.props.noLink
        );
    },

    getUrl(id) {
        const file = this.files.find((attachment) => attachment.id === id);
        return file && file.type === "url" ? file.url : this._super(id);
    },

    getExtension(file) {
        return file.type === "url" ? this.env._t("Link") : this._super(file);
    },

    onAttachLinkClick() {
        this.linkDialog.add(AttachmentLinkDialog, {
            resModel: this.props.record.resModel,
            resId: this.props.record.data.id || 0,
            // Same path as an upload, so variants hooking it see links too.
            onSave: (attachmentId) => this.onFileUploaded([{id: attachmentId}]),
        });
    },

    /**
     * Open a link in a new tab rather than following/downloading it, unless
     * a viewer (agx_photoviewer) already handled the click.
     */
    onLinkClick(ev, file) {
        if (file.type === "url" && !ev.defaultPrevented && ev.target.closest("a")) {
            ev.preventDefault();
            window.open(file.url, "_blank", "noopener");
        }
    },
});
