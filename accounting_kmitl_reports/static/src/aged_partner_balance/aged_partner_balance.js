/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
import { MultiRecordSelect } from "../trial_balance/multi_record_select";

const REPORT_MODEL = "report.accounting_kmitl_reports.aged_partner_balance_kmitl";

// Selected-record state buckets that feed the report options.
const SELECTION_KEYS = ["partners", "accounts", "departments", "sources", "funds", "activities"];

export class AgedPartnerBalance extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        // The tag (set on the menu's client action) selects the account type.
        this.accountType =
            this.props.action.tag === "kmitl_aged_payable" ? "payable" : "receivable";
        this.title = this.accountType === "payable" ? _t("Aged Payable") : _t("Aged Receivable");
        this.fiscalYears = [];
        this.state = useState({
            dateAt: false,
            onlyPosted: true,
            showDetails: false,
            showAdvanced: false,
            // selections (each an Array<{id, name}>)
            partners: [],
            accounts: [],
            departments: [],
            sources: [],
            funds: [],
            activities: [],
            accounts_data: [],
            totals: {},
            loading: false,
        });
        this.labels = {
            partners: _t("Partners"),
            accounts: _t("Accounts"),
            departments: _t("Departments"),
            sources: _t("Sources"),
            funds: _t("Funds"),
            activities: _t("Activities"),
        };
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        this.companyId = this.company.currentCompany.id;
        this.state.dateAt = new Date().toISOString().slice(0, 10);
        await this.load();
    }

    // ------------------------------------------------------------------
    // Report options + data loading
    // ------------------------------------------------------------------
    get options() {
        return {
            company_id: this.companyId,
            account_type: this.accountType,
            date_at: this.state.dateAt,
            only_posted: this.state.onlyPosted,
            show_move_line_details: this.state.showDetails,
            partner_ids: this.state.partners.map((r) => r.id),
            account_ids: this.state.accounts.map((r) => r.id),
            dims: {
                departments: this.state.departments.map((r) => r.id),
                sources: this.state.sources.map((r) => r.id),
                funds: this.state.funds.map((r) => r.id),
                activities: this.state.activities.map((r) => r.id),
            },
        };
    }

    async load() {
        if (!this.state.dateAt) {
            return;
        }
        this.state.loading = true;
        try {
            const data = await this.orm.call(REPORT_MODEL, "get_aged_partner_data", [
                this.options,
            ]);
            this.state.accounts_data = data.accounts || [];
            this.state.totals = data.totals || {};
        } finally {
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------
    // Filter events
    // ------------------------------------------------------------------
    onDateAtChange(ev) {
        this.state.dateAt = ev.target.value || false;
        this.load();
    }

    onTogglePosted(ev) {
        this.state.onlyPosted = ev.target.checked;
        this.load();
    }

    onToggleDetails(ev) {
        this.state.showDetails = ev.target.checked;
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

    // Muted-red class for negative amounts (the minus sign carries the meaning).
    negClass(value) {
        return value < 0 ? "o_kmitl_amount_neg" : "";
    }

    async printPdf() {
        const action = await this.orm.call(REPORT_MODEL, "action_print_pdf", [this.options]);
        await this.action.doAction(action);
    }

    async exportXlsx() {
        const action = await this.orm.call(REPORT_MODEL, "action_export_xlsx", [this.options]);
        await this.action.doAction(action);
    }
}

AgedPartnerBalance.template = "accounting_kmitl_reports.AgedPartnerBalance";
AgedPartnerBalance.components = { MultiRecordSelect };

registry.category("actions").add("kmitl_aged_receivable", AgedPartnerBalance);
registry.category("actions").add("kmitl_aged_payable", AgedPartnerBalance);
