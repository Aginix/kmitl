/** @odoo-module **/

import { Component, useState, useRef, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Small reusable multi-select that searches records with the native
 * ``name_search`` RPC and renders the picks as removable badges. Copied from
 * the accounting_kmitl_reports report screens so this module stays decoupled
 * from that module.
 *
 * Props:
 *  - resModel: model to search
 *  - domain: base domain applied to the search
 *  - placeholder: input placeholder
 *  - selected: Array<{id, name}> currently selected (controlled by parent)
 *  - onChange: called with the new Array<{id, name}>
 */
export class MultiRecordSelect extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({ query: "", open: false, options: [] });
        this.root = useRef("root");
        useExternalListener(window, "mousedown", (ev) => this.onClickAway(ev));
    }

    get selected() {
        return this.props.selected || [];
    }

    onClickAway(ev) {
        if (this.root.el && !this.root.el.contains(ev.target)) {
            this.state.open = false;
        }
    }

    async _search(query) {
        const selectedIds = this.selected.map((r) => r.id);
        const domain = [...(this.props.domain || []), ["id", "not in", selectedIds]];
        const results = await this.orm.call(this.props.resModel, "name_search", [], {
            name: query || "",
            args: domain,
            operator: "ilike",
            limit: 12,
        });
        this.state.options = results.map(([id, name]) => ({ id, name }));
    }

    async onFocus() {
        this.state.open = true;
        await this._search(this.state.query);
    }

    async onInput(ev) {
        this.state.query = ev.target.value;
        this.state.open = true;
        await this._search(this.state.query);
    }

    add(option) {
        this.state.query = "";
        this.state.options = [];
        this.state.open = false;
        this.props.onChange([...this.selected, option]);
    }

    remove(id) {
        this.props.onChange(this.selected.filter((r) => r.id !== id));
    }
}

MultiRecordSelect.template = "budget_revenue_comparison.MultiRecordSelect";
MultiRecordSelect.props = {
    resModel: String,
    domain: { type: Array, optional: true },
    placeholder: { type: String, optional: true },
    selected: { type: Array, optional: true },
    onChange: Function,
};
MultiRecordSelect.defaultProps = {
    domain: [],
    placeholder: "",
    selected: [],
};
