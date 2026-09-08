/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {Component, onWillStart, useState} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";
import {MultiRecordSelect} from "@accounting_kmitl_reports/trial_balance/multi_record_select";

const REPORT_MODEL = "finance_kmitl_reports.payment.report";
const TOTAL_KEY = "amount";

// The four KMITL dimensions, plus the record pickers, all of which are held as
// arrays of {id, name} and sent as plain ids.
const DIMENSION_KEYS = ["departments", "sources", "funds", "activities"];
const RECORD_KEYS = [
    "payingAccounts",
    "methods",
    "partners",
    "payeeTypes",
    "subjects",
    "operationTypes",
];

/**
 * รายงานการจ่ายเงิน — every ใบสำคัญจ่าย the treasury actually paid, on the day
 * the money left rather than the day the voucher was raised.
 *
 * The daily and the monthly report are this screen with two different ranges,
 * so there is one component and no mode.
 */
export class PaymentReport extends Component {
    setup() {
        this.controlPanelDisplay = {"top-left": true, "bottom-right": false};
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
            groupBy: "paid_date",
            groupBy2: "",
            departments: [],
            sources: [],
            funds: [],
            activities: [],
            payingAccounts: [],
            methods: [],
            partners: [],
            payeeTypes: [],
            subjects: [],
            operationTypes: [],
        });
        this.axes = [];
        this.labels = {
            print: _t("Print"),
            exportExcel: _t("Export Excel"),
            empty: _t("No payments for the selected criteria."),
            dateFrom: _t("Paid From"),
            dateTo: _t("Paid To"),
            groupBy: _t("Group By"),
            groupBy2: _t("Then By"),
            none: _t("None"),
            grandTotal: _t("Grand Total"),
            departments: _t("Departments"),
            sources: _t("Sources"),
            funds: _t("Funds"),
            activities: _t("Activities"),
            payingAccount: _t("Paying Account"),
            method: _t("Payment Method"),
            payee: _t("Payee"),
            payeeType: _t("Payee Type"),
            subject: _t("Payment Subject"),
            operationType: _t("Operation Type"),
        };
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        const params = (this.props.action && this.props.action.params) || {};
        this.companyId = params.company_id || this.company.currentCompany.id;
        // Default to the month in progress: the daily reading is one day of it
        // and the monthly reading is all of it, so the month is the range that
        // needs the fewest keystrokes either way. getMonth() is 0-based.
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
            paying_account_ids: this.state.payingAccounts.map((r) => r.id),
            method_ids: this.state.methods.map((r) => r.id),
            partner_ids: this.state.partners.map((r) => r.id),
            payee_type_ids: this.state.payeeTypes.map((r) => r.id),
            subject_ids: this.state.subjects.map((r) => r.id),
            operation_type_ids: this.state.operationTypes.map((r) => r.id),
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

    openPayment(row) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.payment",
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

PaymentReport.template = "finance_kmitl_reports.PaymentReport";
PaymentReport.components = {ControlPanel, MultiRecordSelect};
PaymentReport.props = ["*"];

registry.category("actions").add("finance_kmitl_payment_report", PaymentReport);
