/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {Component, onWillStart, useState} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";
import {MultiRecordSelect} from "@accounting_kmitl_reports/trial_balance/multi_record_select";

const REPORT_MODEL = "finance_kmitl_reports.receipt.report";
const TOTAL_KEY = "amount_total";

// The four KMITL dimensions, plus the record pickers, all of which are held as
// arrays of {id, name} and sent as plain ids.
const DIMENSION_KEYS = ["departments", "sources", "funds", "activities"];
const RECORD_KEYS = ["methods", "partners", "issuingDepartments", "remittances"];

/**
 * รายงานการรับเงิน — every ใบเสร็จรับเงิน whose money has reached the
 * treasury, in the period it was received.
 *
 * The daily and the monthly report are this screen with two different date
 * ranges, so there is one component and no mode — the same arrangement as the
 * payment report on the money-out side.
 */
export class ReceiptReport extends Component {
    setup() {
        // top-right off: the filters moved into the report body (core caps
        // that slot at half the width), and leaving it on would render core's
        // own SearchBar, which a client action has no search model for.
        this.controlPanelDisplay = {
            "top-left": true,
            "top-right": false,
            "bottom-right": false,
        };
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        this.totalKey = TOTAL_KEY;
        this.state = useState({
            loading: true,
            columns: [],
            groups: [],
            grandTotal: 0,
            dateFrom: false,
            dateTo: false,
            groupBy: "date",
            groupBy2: "",
            showAdvanced: false,
            departments: [],
            sources: [],
            funds: [],
            activities: [],
            methods: [],
            partners: [],
            issuingDepartments: [],
            remittances: [],
        });
        this.axes = [];
        this.labels = {
            print: _t("Print"),
            exportExcel: _t("Export Excel"),
            empty: _t("No receipts for the selected criteria."),
            dateFrom: _t("Received From"),
            dateTo: _t("Received To"),
            groupBy: _t("Group By"),
            groupBy2: _t("Then By"),
            none: _t("None"),
            moreFilters: _t("More filters"),
            fewerFilters: _t("Fewer filters"),
            clearFilters: _t("Clear filters"),
            grandTotal: _t("Grand Total"),
            departments: _t("Departments"),
            sources: _t("Sources"),
            funds: _t("Funds"),
            activities: _t("Activities"),
            method: _t("Receiving Method"),
            payer: _t("Payer"),
            issuingDepartment: _t("Issuing Department"),
            remittance: _t("Remittance"),
        };
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        const params = (this.props.action && this.props.action.params) || {};
        this.companyId = params.company_id || this.company.currentCompany.id;
        // Default to the month in progress: the daily reading is one day of
        // it and the monthly reading is all of it, the same default the
        // payment report opens on.
        const now = new Date();
        const pad = (n) => String(n).padStart(2, "0");
        const year = now.getFullYear();
        const month = now.getMonth();
        const lastDay = new Date(year, month + 1, 0).getDate();
        this.state.dateFrom = `${year}-${pad(month + 1)}-01`;
        this.state.dateTo = `${year}-${pad(month + 1)}-${pad(lastDay)}`;
        [this.axes, this.state.columns] = await Promise.all([
            this.orm.call(REPORT_MODEL, "get_group_axes", []),
            this.orm.call(REPORT_MODEL, "get_columns", []),
        ]);
        await this.load();
    }

    get options() {
        return {
            company_id: this.companyId,
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            group_by: this.state.groupBy,
            group_by_2: this.state.groupBy2 || false,
            dims: {
                departments: this.state.departments.map((r) => r.id),
                sources: this.state.sources.map((r) => r.id),
                funds: this.state.funds.map((r) => r.id),
                activities: this.state.activities.map((r) => r.id),
            },
            method_ids: this.state.methods.map((r) => r.id),
            partner_ids: this.state.partners.map((r) => r.id),
            department_ids: this.state.issuingDepartments.map((r) => r.id),
            remittance_ids: this.state.remittances.map((r) => r.id),
        };
    }

    async load() {
        if (!this.state.dateFrom || !this.state.dateTo) {
            return;
        }
        this.state.loading = true;
        try {
            const data = await this.orm.call(REPORT_MODEL, "get_report_data", [
                this.options,
            ]);
            this.state.groups = data.groups || [];
            this.state.grandTotal = data.grand_total || 0;
        } finally {
            this.state.loading = false;
        }
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value || false;
        this.load();
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value || false;
        this.load();
    }

    onGroupByChange(ev) {
        this.state.groupBy = ev.target.value;
        this.load();
    }

    onGroupBy2Change(ev) {
        this.state.groupBy2 = ev.target.value;
        this.load();
    }

    onSelectionChange(key, selected) {
        if (DIMENSION_KEYS.includes(key) || RECORD_KEYS.includes(key)) {
            this.state[key] = selected;
            this.load();
        }
    }

    toggleAdvanced() {
        this.state.showAdvanced = !this.state.showAdvanced;
    }

    /** How many pickers are narrowing the report — shown on the collapse
     * toggle so a filter set while the panel was open is not invisible once
     * it is closed again. */
    get activeFilterCount() {
        return [...DIMENSION_KEYS, ...RECORD_KEYS].filter(
            (key) => this.state[key].length
        ).length;
    }

    clearFilters() {
        for (const key of [...DIMENSION_KEYS, ...RECORD_KEYS]) {
            this.state[key] = [];
        }
        this.load();
    }

    openReceipt(row) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "kmitl.receipt",
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

    cell(row, column) {
        return column[2] ? this.format(row[column[0]]) : row[column[0]];
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

ReceiptReport.template = "finance_kmitl_reports.ReceiptReport";
ReceiptReport.components = {ControlPanel, MultiRecordSelect};
ReceiptReport.props = ["*"];

registry.category("actions").add("finance_kmitl_receipt_report", ReceiptReport);
