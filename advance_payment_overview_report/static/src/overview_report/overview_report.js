/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {useDebounced} from "@web/core/utils/timing";
import {Component, onWillStart, useState} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";
import {MultiRecordSelect} from "@accounting_kmitl_reports/trial_balance/multi_record_select";

const REPORT_MODEL = "advance.payment.overview.report";

// Record pickers, held as arrays of {id, name} and sent as plain ids.
const RECORD_KEYS = ["operatingUnits", "employees", "loanTypes"];
// Plain-value filters, held as arrays of selection codes.
const VALUE_KEYS = ["states", "dueStatuses"];

// Badge colour per loan state.
const STATE_BADGES = {
    to_endorse: "bg-info text-dark",
    to_verify: "bg-info text-dark",
    to_director: "bg-info text-dark",
    to_approve: "bg-info text-dark",
    approved: "bg-warning text-dark",
    in_progress: "bg-primary",
    done: "bg-success",
};
const DUE_BADGES = {
    not_due: "bg-light text-dark border",
    due: "bg-warning text-dark",
    overdue: "bg-danger",
};

/**
 * รายงานภาพรวมสัญญายืมเงิน — every submitted loan with its BC, AR/PR, voucher
 * and DR numbers on one screen, for the loan officer.
 */
export class AdvancePaymentOverviewReport extends Component {
    setup() {
        // Filters live in the body: core's top-right slot is capped at half
        // the width and a client action has no search model for its SearchBar.
        this.controlPanelDisplay = {
            "top-left": true,
            "top-right": false,
            "bottom-right": false,
        };
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        this.state = useState({
            loading: true,
            columns: [],
            groups: [],
            totals: {},
            grouped: false,
            dateFrom: false,
            dateTo: false,
            search: "",
            groupBy: "",
            groupBy2: "",
            showAdvanced: false,
            states: [],
            dueStatuses: [],
            operatingUnits: [],
            employees: [],
            loanTypes: [],
        });
        this.axes = [];
        this.stateChoices = [];
        this.dueChoices = [];
        this.debouncedLoad = useDebounced(() => this.load(), 400);
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        this.companyId = this.company.currentCompany.id;
        const [axes, columns, selections, defaults] = await Promise.all([
            this.orm.call(REPORT_MODEL, "get_group_axes", []),
            this.orm.call(REPORT_MODEL, "get_columns", []),
            this.orm.call(REPORT_MODEL, "get_selections", []),
            this.orm.call(REPORT_MODEL, "get_default_options", []),
        ]);
        this.axes = axes;
        this.state.columns = columns;
        this.stateChoices = selections.states;
        this.dueChoices = selections.return_due_statuses;
        this.state.dateFrom = defaults.date_from;
        this.state.dateTo = defaults.date_to;
        await this.load();
    }

    get options() {
        return {
            company_id: this.companyId,
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            search: this.state.search,
            group_by: this.state.groupBy || false,
            group_by_2: this.state.groupBy2 || false,
            states: this.state.states,
            return_due_statuses: this.state.dueStatuses,
            operating_unit_ids: this.state.operatingUnits.map((r) => r.id),
            employee_ids: this.state.employees.map((r) => r.id),
            loan_type_ids: this.state.loanTypes.map((r) => r.id),
        };
    }

    get rowCount() {
        let count = 0;
        for (const group of this.state.groups) {
            count += group.rows.length;
            for (const sub of group.subgroups) {
                count += sub.rows.length;
            }
        }
        return count;
    }

    async load() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(REPORT_MODEL, "get_report_data", [
                this.options,
            ]);
            this.state.groups = data.groups || [];
            this.state.totals = data.totals || {};
            this.state.grouped = data.grouped;
        } finally {
            this.state.loading = false;
        }
    }

    onDateChange(key, ev) {
        this.state[key] = ev.target.value || false;
        this.load();
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.debouncedLoad();
    }

    onGroupByChange(key, ev) {
        this.state[key] = ev.target.value;
        if (key === "groupBy" && !ev.target.value) {
            this.state.groupBy2 = "";
        }
        this.load();
    }

    toggleValue(key, value) {
        const values = this.state[key];
        this.state[key] = values.includes(value)
            ? values.filter((v) => v !== value)
            : [...values, value];
        this.load();
    }

    onSelectionChange(key, selected) {
        this.state[key] = selected;
        this.load();
    }

    toggleAdvanced() {
        this.state.showAdvanced = !this.state.showAdvanced;
    }

    get activeFilterCount() {
        return [...RECORD_KEYS, ...VALUE_KEYS].filter((key) => this.state[key].length)
            .length;
    }

    clearFilters() {
        for (const key of [...RECORD_KEYS, ...VALUE_KEYS]) {
            this.state[key] = [];
        }
        this.state.search = "";
        this.load();
    }

    openLoan(row) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "advance.payment",
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    /** Blank rather than 0.00 for nothing, as the server formats it. */
    format(value) {
        if (!value || Math.abs(value) < 0.005) {
            return "";
        }
        return value.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    stateBadge(row) {
        return STATE_BADGES[row.state_code] || "bg-secondary";
    }

    dueBadge(row) {
        return DUE_BADGES[row.return_due_status_code] || "";
    }

    lines(value) {
        return value ? value.split("\n") : [];
    }

    async printReport() {
        const action = await this.orm.call(REPORT_MODEL, "action_print_pdf", [
            this.options,
        ]);
        await this.action.doAction(action);
    }

    async exportXlsx() {
        const action = await this.orm.call(REPORT_MODEL, "action_export_xlsx", [
            this.options,
        ]);
        await this.action.doAction(action);
    }
}

AdvancePaymentOverviewReport.template = "advance_payment_overview_report.OverviewReport";
AdvancePaymentOverviewReport.components = {ControlPanel, MultiRecordSelect};
AdvancePaymentOverviewReport.props = ["*"];

registry
    .category("actions")
    .add("advance_payment_overview_report", AdvancePaymentOverviewReport);
