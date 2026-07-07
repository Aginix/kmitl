/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
import { MultiRecordSelect } from "./multi_record_select";

const REPORT_MODEL = "report.accounting_kmitl_reports.trial_balance_kmitl";

// Selected-record state buckets that feed the report options.
const SELECTION_KEYS = [
    "journals",
    "partners",
    "accounts",
    "accountFrom",
    "accountTo",
    "departments",
    "sources",
    "funds",
    "activities",
];

export class TrialBalance extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        this.fiscalYears = [];
        this.state = useState({
            fiscalYearId: false,
            dateFrom: false,
            dateTo: false,
            onlyPosted: true,
            hideAt0: true,
            // Journal/partner/account filters stay collapsed until requested.
            showAdvanced: false,
            // selections (each an Array<{id, name}>)
            journals: [],
            partners: [],
            accounts: [],
            accountFrom: [],
            accountTo: [],
            departments: [],
            sources: [],
            funds: [],
            activities: [],
            // Per-dimension "only the specified entry" toggles. When false
            // (default) a selected node also matches its descendants.
            dimOnlySelf: {
                departments: false,
                funds: false,
                activities: false,
            },
            rows: [],
            totals: {},
            loading: false,
        });
        // Translated placeholders for the dimension / standard selectors.
        this.labels = {
            journals: _t("Journals"),
            partners: _t("Partners"),
            accounts: _t("Accounts"),
            accountFrom: _t("From code"),
            accountTo: _t("To code"),
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

    // ------------------------------------------------------------------
    // Report options + data loading
    // ------------------------------------------------------------------
    get options() {
        return {
            company_id: this.companyId,
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            only_posted: this.state.onlyPosted,
            hide_account_at_0: this.state.hideAt0,
            journal_ids: this.state.journals.map((r) => r.id),
            partner_ids: this.state.partners.map((r) => r.id),
            account_ids: this.state.accounts.map((r) => r.id),
            account_code_from_id: (this.state.accountFrom[0] || {}).id || false,
            account_code_to_id: (this.state.accountTo[0] || {}).id || false,
            dims: {
                departments: this.state.departments.map((r) => r.id),
                sources: this.state.sources.map((r) => r.id),
                funds: this.state.funds.map((r) => r.id),
                activities: this.state.activities.map((r) => r.id),
            },
            dim_only_self: { ...this.state.dimOnlySelf },
        };
    }

    async load() {
        if (!this.state.dateFrom || !this.state.dateTo) {
            return;
        }
        this.state.loading = true;
        try {
            const data = await this.orm.call(REPORT_MODEL, "get_trial_balance_data", [
                this.options,
            ]);
            this.state.rows = data.rows || [];
            this.state.totals = data.totals || {};
        } finally {
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------
    // Filter events
    // ------------------------------------------------------------------
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

    onTogglePosted(ev) {
        this.state.onlyPosted = ev.target.checked;
        this.load();
    }

    onToggleHide(ev) {
        this.state.hideAt0 = ev.target.checked;
        this.load();
    }

    toggleAdvanced() {
        this.state.showAdvanced = !this.state.showAdvanced;
    }

    // One change handler per selection bucket (bound in the template).
    onSelectionChange(key, selected) {
        if (SELECTION_KEYS.includes(key)) {
            this.state[key] = selected;
            this.load();
        }
    }

    // Toggle a dimension's "only the specified entry" flag (no descendants).
    onToggleDimOnlySelf(code, value) {
        this.state.dimOnlySelf[code] = value;
        this.load();
    }

    // ------------------------------------------------------------------
    // Rendering helpers
    // ------------------------------------------------------------------
    format(value) {
        if (!value || Math.abs(value) < 0.005) {
            return "";
        }
        return value.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    // Like format() but renders an exact zero as "0.00" — used by the totals
    // row so a zero sum shows 0.00 instead of a blank cell.
    formatTotal(value) {
        return (value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    // Muted-red class for negative amounts (the minus sign carries the meaning).
    negClass(value) {
        return value < 0 ? "o_kmitl_amount_neg" : "";
    }

    async printPdf() {
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

    async exportCsv() {
        const action = await this.orm.call(REPORT_MODEL, "action_export_csv", [
            this.options,
        ]);
        await this.action.doAction(action);
    }
}

TrialBalance.template = "accounting_kmitl_reports.TrialBalance";
TrialBalance.components = { MultiRecordSelect };

registry.category("actions").add("kmitl_trial_balance", TrialBalance);
