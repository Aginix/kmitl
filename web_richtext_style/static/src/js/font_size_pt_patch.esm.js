/** @odoo-module **/

import {HtmlField} from "@web_editor/js/backend/html_field";
import {patch} from "@web/core/utils/patch";

// Patch OdooEditor's _updateToolbar to show the raw pt value in the font-size
// indicator instead of the computed px value that getComputedStyle returns.
// The browser always returns computed px, so "14pt" shows as "18" without this.
patch(HtmlField.prototype, "web_richtext_style.HtmlFieldFontSizePt", {
    async startWysiwyg(wysiwyg) {
        await this._super(...arguments);
        const editor = wysiwyg && wysiwyg.odooEditor;
        if (!editor) return;

        const _orig = editor._updateToolbar.bind(editor);
        editor._updateToolbar = function (show) {
            _orig(show);
            const fontSizeEl =
                editor.toolbar && editor.toolbar.querySelector("#fontSizeCurrentValue");
            if (!fontSizeEl) return;
            const sel = editor.document.getSelection();
            if (!sel || !sel.rangeCount) return;
            const start = sel.getRangeAt(0).startContainer;
            let node = start.nodeType === 3 ? start.parentElement : start;
            while (node && node !== editor.editable) {
                if (
                    node.style &&
                    node.style.fontSize &&
                    node.style.fontSize.endsWith("pt")
                ) {
                    fontSizeEl.textContent = parseInt(node.style.fontSize, 10);
                    return;
                }
                node = node.parentElement;
            }
        };
    },
});
