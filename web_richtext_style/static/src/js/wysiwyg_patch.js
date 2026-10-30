odoo.define('web_richtext_style.wysiwyg_patch', function (require) {
    'use strict';

    const Wysiwyg = require('web_editor.wysiwyg');

    Wysiwyg.include({
        /**
         * Override _configureToolbar to support the `allowCommandJustify`
         * option. By default Odoo removes #justify from the backend toolbar
         * (non-snippets mode). Detach it before super can remove it, then
         * re-insert it afterwards when the option is enabled.
         */
        _configureToolbar: function (options) {
            const $toolbar = this.toolbar.$el;
            const $justify = options.allowCommandJustify
                ? $toolbar.find('#justify').detach()
                : null;

            this._super.apply(this, arguments);

            if ($justify) {
                $toolbar.find('#decoration').after($justify);
            }
        },
    });
});
