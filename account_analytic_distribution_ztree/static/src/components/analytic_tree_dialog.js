/** @odoo-module **/

import {Component, useState, onWillStart} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {useService} from "@web/core/utils/hooks";

const NODE_FIELDS = ["name", "code", "complete_name", "child_ids"];

function makeNode(record) {
    return {
        id: record.id,
        name: record.name,
        code: record.code,
        complete_name: record.complete_name,
        hasChildren: record.child_ids.length > 0,
        childrenLoaded: false,
        expanded: false,
        children: [],
    };
}

// One row of the tree; recurses into its own children once expanded.
export class AnalyticTreeNode extends Component {
    async onToggle() {
        await this.props.onToggle(this.props.node);
    }

    onSelect() {
        this.props.onSelect(this.props.node);
    }
}
AnalyticTreeNode.template = "account_analytic_distribution_ztree.AnalyticTreeNode";
AnalyticTreeNode.components = {AnalyticTreeNode};
AnalyticTreeNode.props = {
    node: {type: Object},
    onToggle: {type: Function},
    onSelect: {type: Function},
    level: {type: Number},
};

// Hierarchical (parent/child) picker for one analytic plan's accounts,
// opened from the "Browse tree…" option in the distribution widget's
// autocomplete. A search box falls back to the widget's usual flat search
// for when the user already knows the name/code.
export class AnalyticTreeDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            rootNodes: [],
            search: "",
            searchResults: null,
            loading: true,
        });
        onWillStart(async () => {
            this.state.rootNodes = await this.fetchNodes([
                ...this.props.domain,
                ["parent_id", "=", false],
            ]);
            this.state.loading = false;
        });
    }

    async fetchNodes(domain) {
        const records = await this.orm.searchRead(
            "account.analytic.account",
            domain,
            NODE_FIELDS
        );
        return records.map(makeNode);
    }

    async toggleNode(node) {
        if (!node.hasChildren) {
            return;
        }
        if (!node.childrenLoaded) {
            node.children = await this.fetchNodes([
                ...this.props.domain,
                ["parent_id", "=", node.id],
            ]);
            node.childrenLoaded = true;
        }
        node.expanded = !node.expanded;
    }

    selectNode(node) {
        this.props.onSelected(node.id, node.complete_name || node.name);
        this.props.close();
    }

    async onSearchInput(ev) {
        const term = ev.target.value;
        this.state.search = term;
        if (!term) {
            this.state.searchResults = null;
            return;
        }
        const records = await this.orm.searchRead(
            "account.analytic.account",
            [
                ...this.props.domain,
                "|",
                ["name", "ilike", term],
                ["code", "ilike", term],
            ],
            ["complete_name", "code"],
            {limit: 50}
        );
        // Stale-response guard: the user may have kept typing (or cleared the
        // box) while this request was in flight.
        if (this.state.search !== term) {
            return;
        }
        this.state.searchResults = records;
    }

    selectSearchResult(record) {
        this.props.onSelected(record.id, record.complete_name);
        this.props.close();
    }
}
AnalyticTreeDialog.template = "account_analytic_distribution_ztree.AnalyticTreeDialog";
AnalyticTreeDialog.components = {Dialog, AnalyticTreeNode};
AnalyticTreeDialog.props = {
    title: {type: String},
    domain: {type: Array},
    onSelected: {type: Function},
    close: {type: Function},
};
