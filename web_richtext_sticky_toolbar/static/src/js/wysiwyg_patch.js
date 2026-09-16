odoo.define("web_richtext_sticky_toolbar.wysiwyg_patch", function (require) {
    "use strict";

    const Wysiwyg = require("web_editor.wysiwyg");

    // Odoo removes #justify from the backend toolbar by default (non-snippets
    // mode). When stickyToolbar is enabled we always want justify visible, so
    // detach it before super can remove it and re-insert it afterwards.
    Wysiwyg.include({
        _configureToolbar: function (options) {
            const $toolbar = this.toolbar.$el;
            const $justify = options.allowCommandJustify
                ? $toolbar.find("#justify").detach()
                : null;

            this._super.apply(this, arguments);

            if ($justify && $justify.length) {
                $toolbar.find("#decoration").after($justify);
            }
        },
    });
});
