/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {Component, onWillStart, useState} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";
import {MultiRecordSelect} from "@accounting_kmitl_reports/trial_balance/multi_record_select";

const REPORT_MODEL = "finance_kmitl_reports.receivable.due.report";
const TOTAL_KEY = "amount_residual";

const SELECTION_KEYS = [
    "departments",
    "sources",
    "funds",
    "activities",
    "partners",
    "partnerTypes",
];

/**
 * รายงานลูกหนี้ถึงกำหนดชำระ — what is owed to KMITL, and by when. The mirror
 * of the payables due report on the money-in side.
 *
 * Forward-looking, which is what separates it from Aged Receivable: this is
 * the schedule of what falls due, not a picture of how long the ledger has
 * been carrying something.
 */
export class ReceivableDueReport extends Component {
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
            includeOverdue: false,
            groupBy: "invoice_date_due",
            groupBy2: "",
            showAdvanced: false,
            departments: [],
            sources: [],
            funds: [],
            activities: [],
            partners: [],
            partnerTypes: [],
        });
        this.axes = [];
        this.labels = {
            print: _t("Print"),
            exportExcel: _t("Export Excel"),
            empty: _t("Nothing falls due in the selected criteria."),
            dateFrom: _t("Due From"),
            dateTo: _t("Due To"),
            includeOverdue: _t("Include already overdue"),
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
            customer: _t("Customer"),
            partnerType: _t("Partner Type"),
        };
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        const params = (this.props.action && this.props.action.params) || {};
        this.companyId = params.company_id || this.company.currentCompany.id;
        // Today to the end of the month: the question the office opens this
        // screen with is "what still has to come in before the month
        // closes" — the same default the payables due report opens on.
        const now = new Date();
        const pad = (n) => String(n).padStart(2, "0");
        const year = now.getFullYear();
        const month = now.getMonth();
        const lastDay = new Date(year, month + 1, 0).getDate();
        this.state.dateFrom = `${year}-${pad(month + 1)}-${pad(now.getDate())}`;
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
            include_overdue: this.state.includeOverdue,
            group_by: this.state.groupBy,
            group_by_2: this.state.groupBy2 || false,
            dims: {
                departments: this.state.departments.map((r) => r.id),
                sources: this.state.sources.map((r) => r.id),
                funds: this.state.funds.map((r) => r.id),
                activities: this.state.activities.map((r) => r.id),
            },
            partner_ids: this.state.partners.map((r) => r.id),
            partner_type_ids: this.state.partnerTypes.map((r) => r.id),
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

    onIncludeOverdueChange(ev) {
        this.state.includeOverdue = ev.target.checked;
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
        if (SELECTION_KEYS.includes(key)) {
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
        return SELECTION_KEYS.filter((key) => this.state[key].length).length;
    }

    clearFilters() {
        for (const key of SELECTION_KEYS) {
            this.state[key] = [];
        }
        this.load();
    }

    openInvoice(row) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

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

ReceivableDueReport.template = "finance_kmitl_reports.ReceivableDueReport";
ReceivableDueReport.components = {ControlPanel, MultiRecordSelect};
ReceivableDueReport.props = ["*"];

registry
    .category("actions")
    .add("finance_kmitl_receivable_due_report", ReceivableDueReport);
