/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { MultiRecordSelect } from "@accounting_kmitl_reports/trial_balance/multi_record_select";

const REPORT_MODEL = "receipt_kmitl.receipt.report";

const SELECTION_KEYS = ["departments", "sources", "funds", "activities"];

export class ReceiptSummaryReport extends Component {
    setup() {
        this.controlPanelDisplay = { "top-left": true, "bottom-right": false };
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        this.fiscalYears = [];
        this.state = useState({
            loading: true,
            groups: [],
            grandTotal: 0,
            fiscalYearId: false,
            dateFrom: false,
            dateTo: false,
            paymentType: false,
            departments: [],
            sources: [],
            funds: [],
            activities: [],
        });
        this.labels = {
            print: _t("Print"),
            exportExcel: _t("Export Excel"),
            empty: _t("No receipts for the selected criteria."),
            date: _t("Date"),
            number: _t("Receipt No."),
            description: _t("Description"),
            amount: _t("Amount"),
            dimensions: _t("Analytic Dimensions"),
            note: _t("Note"),
            total: _t("Total"),
            grandTotal: _t("Grand Total"),
            departments: _t("Departments"),
            sources: _t("Sources"),
            funds: _t("Funds"),
            activities: _t("Activities"),
        };
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        this.companyId = this.company.currentCompany.id;
        this.fiscalYears = await this.orm.searchRead(
            "account.fiscal.year",
            [],
            ["id", "name", "date_from", "date_to"],
            { order: "date_from desc" }
        );
        const today = new Date().toISOString().slice(0, 10);
        const covering = this.fiscalYears.find(
            (fy) => fy.date_from <= today && fy.date_to >= today
        );
        const fy = covering || this.fiscalYears[0];
        if (fy) {
            this.state.fiscalYearId = fy.id;
            this.state.dateFrom = fy.date_from;
            this.state.dateTo = fy.date_to;
        } else {
            const year = new Date().getFullYear();
            this.state.dateFrom = `${year}-01-01`;
            this.state.dateTo = `${year}-12-31`;
        }
        await this.load();
    }

    get options() {
        return {
            company_id: this.companyId,
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            payment_type: this.state.paymentType || false,
            dims: {
                departments: this.state.departments.map((r) => r.id),
                sources: this.state.sources.map((r) => r.id),
                funds: this.state.funds.map((r) => r.id),
                activities: this.state.activities.map((r) => r.id),
            },
        };
    }

    async load() {
        if (!this.state.dateFrom || !this.state.dateTo) return;
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                REPORT_MODEL,
                "get_report_data",
                [this.options]
            );
            this.state.groups = data.groups || [];
            this.state.grandTotal = data.grand_total || 0;
        } finally {
            this.state.loading = false;
        }
    }

    onFiscalYearChange(ev) {
        const id = parseInt(ev.target.value) || false;
        this.state.fiscalYearId = id;
        const fy = this.fiscalYears.find((f) => f.id === id);
        if (fy) {
            this.state.dateFrom = fy.date_from;
            this.state.dateTo = fy.date_to;
        }
        this.load();
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value || false;
        this.load();
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value || false;
        this.load();
    }

    onPaymentTypeChange(ev) {
        this.state.paymentType = ev.target.value || false;
        this.load();
    }

    onSelectionChange(key, selected) {
        if (SELECTION_KEYS.includes(key)) {
            this.state[key] = selected;
            this.load();
        }
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

    format(value) {
        if (!value || Math.abs(value) < 0.005) return "";
        return value.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
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

ReceiptSummaryReport.template = "receipt_kmitl_summary_report.ReceiptSummaryReport";
ReceiptSummaryReport.components = { ControlPanel, MultiRecordSelect };
ReceiptSummaryReport.props = ["*"];

registry
    .category("actions")
    .add("receipt_kmitl_summary_report", ReceiptSummaryReport);
