/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart } from "@odoo/owl";
import { MultiRecordSelect } from "./multi_record_select";

const DR_FIELDS = [
    "name",
    "date",
    "user_id",
    "amount_total",
    "amount_net",
    "note",
    "department_analytic_id",
    "source_analytic_id",
    "fund_analytic_id",
    "activity_analytic_id",
];

const LINE_FIELDS = ["partner_id", "name", "quantity", "price_unit", "price_subtotal"];

// Filter buckets backed by the MultiRecordSelect widget -> DR search field.
// fund/activity are computed non-stored on the DR (no search) so they are not
// offered as filters, only shown in the expanded detail.
const FILTER_FIELDS = {
    departments: "department_analytic_id",
    sources: "source_analytic_id",
    partners: "line_ids.partner_id",
};

// The two approver stages, keyed by the client action's context.approval_stage.
const STAGES = {
    finance: {
        state: "pending_finance",
        method: "action_approve_finance",
        title: _t("Awaiting Finance Director approval"),
    },
    rector: {
        state: "pending_rector",
        method: "action_approve",
        title: _t("Awaiting Rector-delegated approval"),
    },
};

export class ApprovalQueue extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.company = useService("company");
        this.fiscalYears = [];
        this.stage = STAGES[this.props.action.context.approval_stage] || STAGES.finance;
        this.state = useState({
            loading: true,
            requests: [],
            expandedId: null,
            linesById: {},
            selectedIds: [],
            fiscalYearId: false,
            dateFrom: false,
            dateTo: false,
            showAdvanced: false,
            departments: [],
            sources: [],
            partners: [],
        });
        // All UI labels go through _t so they are extracted for i18n.
        this.labels = {
            title: this.stage.title,
            approveSelected: _t("Approve Selected"),
            empty: _t("No requests pending your approval."),
            number: _t("Number"),
            date: _t("Date"),
            responsible: _t("Responsible"),
            total: _t("Total"),
            net: _t("Net Total"),
            actions: _t("Actions"),
            approve: _t("Approve"),
            reject: _t("Reject"),
            payee: _t("Payee"),
            description: _t("Description"),
            quantity: _t("Quantity"),
            unitPrice: _t("Unit Price"),
            subtotal: _t("Subtotal"),
            department: _t("Department"),
            source: _t("Source"),
            fund: _t("Fund"),
            activity: _t("Activity"),
            note: _t("Note"),
            open: _t("Open"),
            fiscalYear: _t("Fiscal Year"),
            dateFrom: _t("Date From"),
            dateTo: _t("Date To"),
            departments: _t("Departments"),
            sources: _t("Sources"),
            partners: _t("Partners"),
            moreFilters: _t("More filters"),
            hideFilters: _t("Hide filters"),
        };
        onWillStart(async () => {
            this.companyId = this.company.currentCompany.id;
            this.fiscalYears = await this.orm.searchRead(
                "account.fiscal.year",
                [],
                ["id", "name", "date_from", "date_to"],
                { order: "date_from desc" }
            );
            await this.loadRequests();
        });
    }

    get domain() {
        const domain = [["approval_state", "=", this.stage.state]];
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

    async loadRequests() {
        this.state.loading = true;
        this.state.requests = await this.orm.searchRead(
            "disbursement.request",
            this.domain,
            DR_FIELDS,
            { order: "date desc, id desc" }
        );
        const ids = this.state.requests.map((dr) => dr.id);
        this.state.selectedIds = this.state.selectedIds.filter((id) =>
            ids.includes(id)
        );
        this.state.expandedId = null;
        this.state.loading = false;
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
        this.loadRequests();
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value || false;
        this.loadRequests();
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value || false;
        this.loadRequests();
    }

    toggleAdvanced() {
        this.state.showAdvanced = !this.state.showAdvanced;
    }

    onSelectionChange(key, selected) {
        if (Object.prototype.hasOwnProperty.call(FILTER_FIELDS, key)) {
            this.state[key] = selected;
            this.loadRequests();
        }
    }

    isFiscalYearSelected(fyId) {
        return fyId === this.state.fiscalYearId;
    }

    // ------------------------------------------------------------------
    // Rows
    // ------------------------------------------------------------------
    openRequest(dr) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "disbursement.request",
            res_id: dr.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async toggleExpand(dr) {
        if (this.state.expandedId === dr.id) {
            this.state.expandedId = null;
            return;
        }
        if (!this.state.linesById[dr.id]) {
            this.state.linesById[dr.id] = await this.orm.searchRead(
                "disbursement.request.line",
                [["request_id", "=", dr.id]],
                LINE_FIELDS
            );
        }
        this.state.expandedId = dr.id;
    }

    async approve(dr) {
        await this.orm.call("disbursement.request", this.stage.method, [[dr.id]]);
        this.notification.add(_t("Approved"), { type: "success" });
        await this.loadRequests();
    }

    async reject(dr) {
        const action = await this.orm.call(
            "disbursement.request",
            "action_open_reject_wizard",
            [[dr.id]]
        );
        this.action.doAction(action, { onClose: () => this.loadRequests() });
    }

    async approveSelected() {
        if (!this.state.selectedIds.length) {
            return;
        }
        const action = await this.orm.call(
            "disbursement.request",
            "action_approve_batch",
            [this.state.selectedIds]
        );
        if (action) {
            await this.action.doAction(action);
        }
        await this.loadRequests();
    }

    toggleSelect(drId) {
        const selected = this.state.selectedIds;
        if (selected.includes(drId)) {
            this.state.selectedIds = selected.filter((id) => id !== drId);
        } else {
            this.state.selectedIds = [...selected, drId];
        }
    }

    isSelected(drId) {
        return this.state.selectedIds.includes(drId);
    }

    toggleSelectAll() {
        this.state.selectedIds = this.allSelected
            ? []
            : this.state.requests.map((dr) => dr.id);
    }

    get allSelected() {
        return (
            this.state.requests.length > 0 &&
            this.state.selectedIds.length === this.state.requests.length
        );
    }

    displayName(value) {
        // Many2one searchRead value is [id, display_name] or false.
        return Array.isArray(value) ? value[1] : "";
    }

    formatCurrency(amount) {
        return (amount || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
}

ApprovalQueue.template = "disbursement.ApprovalQueue";
ApprovalQueue.components = { MultiRecordSelect };
ApprovalQueue.props = ["*"];

registry.category("actions").add("disbursement.approval_queue", ApprovalQueue);
