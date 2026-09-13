/** @odoo-module **/

import { Component, useState, useRef, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Small reusable multi-select that searches records with ``name_search`` and
 * renders the picks as removable badges. Copied (trimmed) from
 * budget_revenue_comparison so this module stays self-contained.
 *
 * Props: resModel, domain, placeholder, selected (Array<{id,name}>), onChange.
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

MultiRecordSelect.template = "procurement_plan_report.MultiRecordSelect";
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
