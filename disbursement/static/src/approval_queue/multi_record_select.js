/** @odoo-module **/

import { Component, useState, useRef, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * A small reusable multi-select / single-select that searches records with
 * the native ``name_search`` RPC and renders the picks as removable badges.
 * Used for the department / source / partner filters on the approval queue
 * (mirrors accounting_kmitl_workflow's queue widget).
 *
 * Props:
 *  - resModel: model to search
 *  - domain: base domain applied to the search
 *  - placeholder: input placeholder
 *  - single: keep at most one selection
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

    get inputVisible() {
        return !this.props.single || this.selected.length === 0;
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
        const next = this.props.single ? [option] : [...this.selected, option];
        this.state.query = "";
        this.state.options = [];
        this.state.open = false;
        this.props.onChange(next);
    }

    remove(id) {
        this.props.onChange(this.selected.filter((r) => r.id !== id));
    }
}

MultiRecordSelect.template = "disbursement.MultiRecordSelect";
MultiRecordSelect.props = {
    resModel: String,
    domain: { type: Array, optional: true },
    placeholder: { type: String, optional: true },
    single: { type: Boolean, optional: true },
    selected: { type: Array, optional: true },
    onChange: Function,
};
MultiRecordSelect.defaultProps = {
    domain: [],
    placeholder: "",
    single: false,
    selected: [],
};
