/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {MisReportWidget} from "@mis_builder/components/mis_report_widget.esm";

patch(MisReportWidget.prototype, "mis_builder_hierarchy", {
    setup() {
        this._super(...arguments);
        this.state.collapsed = {};
        this._hiddenKeysCache = null;
        this._hiddenKeysBody = null;
        this._hiddenKeysCollapsed = null;
    },

    toggleRow(rowKey) {
        this.state.collapsed = {
            ...this.state.collapsed,
            [rowKey]: !this.state.collapsed[rowKey],
        };
    },

    get hiddenKeys() {
        const body = this.state.mis_report_data.body || [];
        const collapsed = this.state.collapsed;
        if (
            this._hiddenKeysCache &&
            this._hiddenKeysBody === body &&
            this._hiddenKeysCollapsed === collapsed
        ) {
            return this._hiddenKeysCache;
        }
        const byKey = {};
        for (const r of body) {
            if (r.row_key) {
                byKey[r.row_key] = r;
            }
        }
        const hidden = new Set();
        for (const r of body) {
            let key = r.parent_row_key;
            while (key) {
                if (collapsed[key]) {
                    hidden.add(r.row_key);
                    break;
                }
                key = byKey[key] ? byKey[key].parent_row_key : null;
            }
        }
        this._hiddenKeysCache = hidden;
        this._hiddenKeysBody = body;
        this._hiddenKeysCollapsed = collapsed;
        return hidden;
    },

    isRowHidden(row) {
        if (!row.parent_row_key) {
            return false;
        }
        return this.hiddenKeys.has(row.row_key);
    },
});
