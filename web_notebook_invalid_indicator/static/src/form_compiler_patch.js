/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormRenderer } from "@web/views/form/form_renderer";
import { getModifier } from "@web/views/view_compiler";

const INVALID_CLASS = "o_notebook_page_invalid";

function collectPageFieldNames(pageEl) {
    const own = pageEl.querySelectorAll("field[name]");
    const nested = new Set(pageEl.querySelectorAll("notebook page field[name]"));
    const names = new Set();
    for (const field of own) {
        if (nested.has(field)) {
            continue;
        }
        names.add(field.getAttribute("name"));
    }
    return [...names];
}

patch(FormRenderer.prototype, "web_notebook_invalid_indicator", {
    hasInvalidNotebookField(fieldNames) {
        const record = this.props.record;
        if (!record || !record._invalidFields || !record._invalidFields.size) {
            return false;
        }
        for (const fieldName of fieldNames) {
            if (record._invalidFields.has(fieldName)) {
                return true;
            }
        }
        return false;
    },
});

patch(FormCompiler.prototype, "web_notebook_invalid_indicator", {
    compileNotebook(el, params) {
        const noteBook = this._super(el, params);

        const pageSlots = [...noteBook.children].filter(
            (c) => c.nodeName.toLowerCase() === "t" && c.hasAttribute("t-set-slot")
        );

        let slotIdx = 0;
        for (const child of el.children) {
            if (child.nodeName.toLowerCase() !== "page") {
                continue;
            }
            const invisible = getModifier(child, "invisible");
            if (this.isAlwaysInvisible(invisible, params)) {
                continue;
            }
            const pageSlot = pageSlots[slotIdx++];
            if (!pageSlot) {
                continue;
            }
            const fieldNames = collectPageFieldNames(child);
            const originalExpr = pageSlot.getAttribute("className") || '""';
            const invalidCheck = fieldNames.length
                ? `this.hasInvalidNotebookField(${JSON.stringify(fieldNames)})`
                : "false";
            pageSlot.setAttribute(
                "className",
                `(${originalExpr}) + (${invalidCheck} ? " ${INVALID_CLASS}" : "")`
            );
        }

        return noteBook;
    },
});
