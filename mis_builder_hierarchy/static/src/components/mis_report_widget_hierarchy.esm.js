/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {MisReportWidget} from "@mis_builder/components/mis_report_widget.esm";

patch(MisReportWidget.prototype, "mis_builder_hierarchy", {
    setup() {
        this._super(...arguments);
        this.state.collapsed = {};
    },

    toggleRow(rowKey) {
        this.state.collapsed = {
            ...this.state.collapsed,
            [rowKey]: !this.state.collapsed[rowKey],
        };
    },

    isRowHidden(row) {
        if (!row.parent_row_key) {
            return false;
        }
        const body = this.state.mis_report_data.body || [];
        const byKey = {};
        for (const r of body) {
            if (r.row_key) {
                byKey[r.row_key] = r;
            }
        }
        let key = row.parent_row_key;
        while (key) {
            if (this.state.collapsed[key]) {
                return true;
            }
            const parent = byKey[key];
            key = parent ? parent.parent_row_key : null;
        }
        return false;
    },

    rowIndentStyle(row) {
        const level = row.level || 0;
        if (!level) {
            return "";
        }
        return `padding-left: ${level * 1.5}em;`;
    },
});
