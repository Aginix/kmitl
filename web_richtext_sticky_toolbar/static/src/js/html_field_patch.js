/** @odoo-module **/

import { HtmlField } from "@web_editor/js/backend/html_field";
import { patch } from "@web/core/utils/patch";

const _originalExtractProps = HtmlField.extractProps;
HtmlField.extractProps = (args) => {
    const props = _originalExtractProps(args);
    const { attrs } = args;
    if (attrs.options.stickyToolbar) {
        props.wysiwygOptions.autohideToolbar = false;
        props.wysiwygOptions.stickyToolbar = true;
    }
    return props;
};

patch(HtmlField.prototype, "web_richtext_sticky_toolbar.HtmlField", {
    async startWysiwyg(wysiwyg) {
        await this._super(...arguments);
        if (this.wysiwyg.options.stickyToolbar) {
            this.wysiwyg.toolbar.$el
                .addClass("o_sticky_toolbar")
                .insertBefore(this.wysiwyg.$editable);
        }
    },
});
