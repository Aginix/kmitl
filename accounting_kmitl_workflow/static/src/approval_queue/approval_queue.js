/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { SearchModel } from "@web/search/search_model";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { Component, useState, useSubEnv, onWillStart } from "@odoo/owl";
import { MultiRecordSelect } from "./multi_record_select";

const MOVE_FIELDS = [
    "name",
    "date",
    "partner_id",
    "journal_id",
    "submitted_by",
    "submitted_date",
    "amount_total",
    "narration",
    "activity_analytic_id",
    "department_analytic_id",
    "fund_analytic_id",
    "source_analytic_id",
];

const LINE_FIELDS = ["account_id", "name", "debit", "credit"];

// Filter buckets backed by the MultiRecordSelect widget -> move field.
// Journal, dimensions, submitter and partner type live in the search panel.
const FILTER_FIELDS = {
    partners: "partner_id",
};

export class ApprovalQueue extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.fiscalYears = [];
        // Odoo's own search model drives the left search panel (sections come
        // from the <searchpanel> of the search view passed in action params).
        this.searchModel = new SearchModel(this.env, {
            user: useService("user"),
            orm: this.orm,
            view: useService("view"),
        });
        useSubEnv({ searchModel: this.searchModel });
        useBus(this.searchModel, "update", () => this.loadMoves());
        this.state = useState({
            loading: true,
            moves: [],
            expandedId: null,
            linesByMove: {},
            selectedIds: [],
            // Filters (mirror the trial-balance report's filter bar).
            fiscalYearId: false,
            dateFrom: false,
            dateTo: false,
            partners: [],
        });
        // All UI labels go through _t so they are extracted for i18n.
        this.labels = {
            title: _t("Pending Approval"),
            approveSelected: _t("Approve Selected"),
            empty: _t("No entries pending approval."),
            number: _t("Number"),
            date: _t("Date"),
            partner: _t("Partner"),
            journal: _t("Journal"),
            submittedBy: _t("Submitted By"),
            submitted: _t("Submitted"),
            total: _t("Total"),
            actions: _t("Actions"),
            approve: _t("Approve"),
            reject: _t("Reject"),
            account: _t("Account"),
            label: _t("Label"),
            debit: _t("Debit"),
            credit: _t("Credit"),
            department: _t("Department"),
            source: _t("Source"),
            fund: _t("Fund"),
            activity: _t("Activity"),
            narration: _t("Narration"),
            open: _t("Open"),
            // Filter labels / placeholders.
            fiscalYear: _t("Fiscal Year"),
            dateFrom: _t("Date From"),
            dateTo: _t("Date To"),
            partners: _t("Partners"),
            selectedTotal: _t("Selected Total"),
        };
        onWillStart(async () => {
            await this.searchModel.load({
                resModel: "account.move",
                searchViewId: this.props.action.params.search_view_id,
                domain: this.filterDomain,
                display: { controlPanel: false },
            });
            this.fiscalYears = await this.orm.searchRead(
                "account.fiscal.year",
                [],
                ["id", "name", "date_from", "date_to"],
                { order: "date_from desc" }
            );
            await this.loadMoves();
        });
    }

    // Queue + filter-bar domain; the search model adds the panel selections.
    get filterDomain() {
        const domain = [["workflow_state", "=", "to_approve"]];
        if (this.state.dateFrom) {
            domain.push(["date", ">=", this.state.dateFrom]);
        }
        if (this.state.dateTo) {
            domain.push(["date", "<=", this.state.dateTo]);
        }
        for (const [key, field] of Object.entries(FILTER_FIELDS)) {
            const ids = this.state[key].map((record) => record.id);
            if (ids.length) {
                domain.push([field, "in", ids]);
            }
        }
        return domain;
    }

    async loadMoves() {
        this.state.loading = true;
        this.state.moves = await this.orm.searchRead(
            "account.move",
            this.searchModel.domain,
            MOVE_FIELDS,
            { order: "date desc, id desc" }
        );
        const ids = this.state.moves.map((move) => move.id);
        this.state.selectedIds = this.state.selectedIds.filter((id) =>
            ids.includes(id)
        );
        this.state.expandedId = null;
        this.state.loading = false;
    }

    async refresh() {
        // Reload the panel counters too; its "update" reloads the moves.
        await this.searchModel.reload({ domain: this.filterDomain });
        this.searchModel.trigger("update");
    }

    // ------------------------------------------------------------------
    // Filters
    // ------------------------------------------------------------------
    onFiscalYearChange(ev) {
        const id = parseInt(ev.target.value) || false;
        this.state.fiscalYearId = id;
        const fy = this.fiscalYears.find((f) => f.id === id);
        this.state.dateFrom = fy ? fy.date_from : false;
        this.state.dateTo = fy ? fy.date_to : false;
        this.refresh();
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value || false;
        this.refresh();
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value || false;
        this.refresh();
    }

    onSelectionChange(key, selected) {
        if (Object.prototype.hasOwnProperty.call(FILTER_FIELDS, key)) {
            this.state[key] = selected;
            this.refresh();
        }
    }

    isFiscalYearSelected(fyId) {
        return fyId === this.state.fiscalYearId;
    }

    // ------------------------------------------------------------------
    // Rows
    // ------------------------------------------------------------------
    openMove(move) {
        // Open the underlying account.move (the real document) form.
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: move.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async toggleExpand(move) {
        if (this.state.expandedId === move.id) {
            this.state.expandedId = null;
            return;
        }
        if (!this.state.linesByMove[move.id]) {
            this.state.linesByMove[move.id] = await this.orm.searchRead(
                "account.move.line",
                [
                    ["move_id", "=", move.id],
                    ["display_type", "not in", ["line_section", "line_note"]],
                ],
                LINE_FIELDS
            );
        }
        this.state.expandedId = move.id;
    }

    async approve(move) {
        await this.orm.call("account.move", "action_approve", [[move.id]]);
        this.notification.add(_t("Approved"), { type: "success" });
        await this.refresh();
    }

    async reject(move) {
        const action = await this.orm.call(
            "account.move",
            "action_open_reject_wizard",
            [[move.id]]
        );
        this.action.doAction(action, { onClose: () => this.refresh() });
    }

    async approveSelected() {
        if (!this.state.selectedIds.length) {
            return;
        }
        const action = await this.orm.call(
            "account.move",
            "action_approve_batch",
            [this.state.selectedIds]
        );
        if (action) {
            await this.action.doAction(action);
        }
        await this.refresh();
    }

    toggleSelect(moveId) {
        const selected = this.state.selectedIds;
        if (selected.includes(moveId)) {
            this.state.selectedIds = selected.filter((id) => id !== moveId);
        } else {
            this.state.selectedIds = [...selected, moveId];
        }
    }

    isSelected(moveId) {
        return this.state.selectedIds.includes(moveId);
    }

    toggleSelectAll() {
        this.state.selectedIds = this.allSelected
            ? []
            : this.state.moves.map((move) => move.id);
    }

    get allSelected() {
        return (
            this.state.moves.length > 0 &&
            this.state.selectedIds.length === this.state.moves.length
        );
    }

    get selectedTotal() {
        return this.state.moves
            .filter((move) => this.isSelected(move.id))
            .reduce((sum, move) => sum + (move.amount_total || 0), 0);
    }

    displayName(value) {
        // Many2one searchRead value is [id, display_name] or false.
        return Array.isArray(value) ? value[1] : "";
    }

    plainText(html) {
        // narration is an Html field; show its text, not the raw markup.
        if (!html) {
            return "";
        }
        const tmp = document.createElement("div");
        tmp.innerHTML = html;
        return (tmp.textContent || "").trim();
    }

    formatCurrency(amount) {
        return (amount || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
}

ApprovalQueue.template = "accounting_kmitl_workflow.ApprovalQueue";
ApprovalQueue.components = { MultiRecordSelect, SearchPanel };
ApprovalQueue.props = ["*"];

registry
    .category("actions")
    .add("accounting_kmitl_workflow.approval_queue", ApprovalQueue);
