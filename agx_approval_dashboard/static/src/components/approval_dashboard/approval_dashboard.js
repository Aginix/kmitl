/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

const SEARCH_MIN_CHARS = 3;
const SEARCH_DEBOUNCE_MS = 200;

export class ApprovalDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.router = useService("router");

        this.state = useState({
            groups: [],
            categoriesByGroup: {},
            selectedGroupId: null,
            searchText: "",
            loading: true,
        });

        this._searchTimer = null;

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;

        const [groups, categories] = await Promise.all([
            this.orm.searchRead(
                "approval.category.group",
                [],
                ["id", "name", "sequence"],
                {order: "sequence, id"}
            ),
            this.orm.searchRead(
                "approval.category",
                [["active", "=", true]],
                ["id", "name", "image", "group_id", "sequence"],
                {order: "sequence, name"}
            ),
        ]);

        const byGroup = {};
        for (const cat of categories) {
            const gid = cat.group_id && cat.group_id[0];
            if (!gid) continue;
            (byGroup[gid] = byGroup[gid] || []).push(cat);
        }

        // Hide groups without any active categories (D8.3)
        const nonEmpty = groups.filter((g) => byGroup[g.id] && byGroup[g.id].length);

        this.state.groups = nonEmpty;
        this.state.categoriesByGroup = byGroup;

        // Restore selection from URL hash if valid, else first group (D8.1/D8.2)
        const hashGid = this._readGroupIdFromHash();
        const initial =
            (hashGid && nonEmpty.find((g) => g.id === hashGid) && hashGid) ||
            (nonEmpty[0] && nonEmpty[0].id) ||
            null;
        this.state.selectedGroupId = initial;
        if (initial) {
            this.router.pushState({group_id: initial});
        }

        this.state.loading = false;
    }

    _readGroupIdFromHash() {
        const raw = this.router.current.hash && this.router.current.hash.group_id;
        if (!raw) return null;
        const n = parseInt(raw, 10);
        return Number.isNaN(n) ? null : n;
    }

    // ──────────────────────────────────────────────────────────────────
    // Derived data
    // ──────────────────────────────────────────────────────────────────

    get selectedGroupCategories() {
        const gid = this.state.selectedGroupId;
        return (gid && this.state.categoriesByGroup[gid]) || [];
    }

    get filteredCategories() {
        const q = (this.state.searchText || "").trim().toLowerCase();
        const list = this.selectedGroupCategories;
        if (q.length < SEARCH_MIN_CHARS) return list;
        return list.filter((c) => (c.name || "").toLowerCase().includes(q));
    }

    get selectedGroupName() {
        const gid = this.state.selectedGroupId;
        const g = this.state.groups.find((x) => x.id === gid);
        return g ? g.name : "";
    }

    get resultCount() {
        return this.filteredCategories.length;
    }

    isGroupActive(groupId) {
        return this.state.selectedGroupId === groupId;
    }

    imageUrl(categoryId) {
        return `/web/image?model=approval.category&field=image&id=${categoryId}`;
    }

    // ──────────────────────────────────────────────────────────────────
    // Event handlers
    // ──────────────────────────────────────────────────────────────────

    onSidebarClick(groupId) {
        if (this.state.selectedGroupId === groupId) return;
        this.state.selectedGroupId = groupId;
        this.state.searchText = "";
        this.router.pushState({group_id: groupId});
    }

    onSearchInput(ev) {
        const value = ev.target.value;
        if (this._searchTimer) {
            clearTimeout(this._searchTimer);
        }
        this._searchTimer = setTimeout(() => {
            this.state.searchText = value;
        }, SEARCH_DEBOUNCE_MS);
    }

    onClearSearch() {
        if (this._searchTimer) {
            clearTimeout(this._searchTimer);
            this._searchTimer = null;
        }
        this.state.searchText = "";
        const input = document.querySelector(".o_ad_search_input");
        if (input) input.value = "";
    }

    onCardClick(categoryId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "approval.request",
            views: [[false, "form"]],
            target: "current",
            context: {
                form_view_initial_mode: "edit",
                default_category_id: categoryId,
            },
        });
    }
}

ApprovalDashboard.template = "agx_approval_dashboard.ApprovalDashboard";
ApprovalDashboard.components = {};

registry.category("actions").add("agx_approval_dashboard", ApprovalDashboard);
