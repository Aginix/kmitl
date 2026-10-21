/** @odoo-module **/

import {normalizeLinkUrl, parseOdooLink} from "@web_attachment_link/link_utils";
import {Dialog} from "@web/core/dialog/dialog";
import {useService} from "@web/core/utils/hooks";
import {Component, useState} from "@odoo/owl";

/**
 * Attach a Link Attachment to `resModel`/`resId`: the user types a URL and a
 * name, onSave(attachmentId) receives the created `ir.attachment`.
 */
export class AttachmentLinkDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({url: "", name: "", error: "", saving: false});
    }

    get invalidMessage() {
        return this.env._t(
            "Enter a web address (http or https) or a link to a document in Odoo."
        );
    }

    /** Name an Odoo Link after its record, unless the user named it already. */
    async onUrlChange() {
        const url = normalizeLinkUrl(this.state.url);
        this.state.error = url || !this.state.url.trim() ? "" : this.invalidMessage;
        if (url && parseOdooLink(url) && !this.state.name.trim()) {
            const info = await this.orm.call("ir.attachment", "get_odoo_link_info", [
                url,
            ]);
            if (info.name && !this.state.name.trim()) {
                this.state.name = info.name;
            }
        }
    }

    async onSave() {
        const url = normalizeLinkUrl(this.state.url);
        if (!url) {
            this.state.error = this.invalidMessage;
            return;
        }
        this.state.saving = true;
        try {
            // One values dict: Odoo 16 passes it as `create(vals)`, returning an id.
            const attachmentId = await this.orm.create("ir.attachment", [
                {
                    name: this.state.name.trim() || url,
                    type: "url",
                    url,
                    res_model: this.props.resModel,
                    res_id: this.props.resId,
                },
            ]);
            await this.props.onSave(attachmentId);
            this.props.close();
        } finally {
            this.state.saving = false;
        }
    }
}

AttachmentLinkDialog.template = "web_attachment_link.AttachmentLinkDialog";
AttachmentLinkDialog.components = {Dialog};
AttachmentLinkDialog.props = {
    resModel: {type: String, optional: true},
    resId: {type: Number, optional: true},
    onSave: Function,
    close: Function,
};
