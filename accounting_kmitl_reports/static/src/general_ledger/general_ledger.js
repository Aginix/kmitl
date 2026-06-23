/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";

const REPORT_MODEL = "report.accounting_kmitl_reports.general_ledger_kmitl";
const WIZARD_ACTION = "accounting_kmitl_reports.action_general_ledger_wizard_kmitl";
// Fields of the journal entry's lines shown in the expand panel (Dr/Cr table).
const ENTRY_LINE_FIELDS = ["account_id", "debit", "credit"];

export class GeneralLedger extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        this.state = useState({
            loading: true,
            accounts: [],
            // Accordion: the id of the expanded move-line (one open at a time).
            expandedId: null,
            // Lazily-fetched Dr/Cr breakdown of each journal entry, by move id.
            linesByMove: {},
            dateFrom: false,
            dateTo: false,
        });
        this.labels = {
            title: _t("General Ledger"),
            changeCriteria: _t("Change criteria"),
            printPdf: _t("Print PDF"),
            exportExcel: _t("Export Excel"),
            empty: _t("No entries for the selected criteria."),
            opening: _t("Opening Balance"),
            carried: _t("Carried Forward"),
            date: _t("Date"),
            issue: _t("Issue"),
            remark: _t("Remark"),
            debit: _t("Debit"),
            credit: _t("Credit"),
            balance: _t("Balance"),
            account: _t("Account"),
            partner: _t("Partner"),
            narration: _t("Narration"),
            maker: _t("Maker"),
            open: _t("Open"),
        };
        onWillStart(this.onWillStart.bind(this));
    }

    async onWillStart() {
        const params = (this.props.action && this.props.action.params) || {};
        this.companyId = params.company_id || this.company.currentCompany.id;
        this.accountIds = params.account_ids || [];
        this.onlyPosted = params.only_posted === undefined ? true : params.only_posted;

        if (params.date_from && params.date_to) {
            this.state.dateFrom = params.date_from;
            this.state.dateTo = params.date_to;
        } else {
            const fys = await this.orm.searchRead(
                "account.fiscal.year",
                [],
                ["date_from", "date_to"],
                { order: "date_from desc" }
            );
            const today = new Date().toISOString().slice(0, 10);
            const fy =
                fys.find((f) => f.date_from <= today && f.date_to >= today) || fys[0];
            if (fy) {
                this.state.dateFrom = fy.date_from;
                this.state.dateTo = fy.date_to;
            } else {
                const year = new Date().getFullYear();
                this.state.dateFrom = `${year}-01-01`;
                this.state.dateTo = `${year}-12-31`;
            }
        }
        await this.load();
    }

    get options() {
        return {
            company_id: this.companyId,
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
            only_posted: this.onlyPosted,
            hide_account_at_0: !this.accountIds.length,
            account_ids: this.accountIds,
            dims: {},
        };
    }

    async load() {
        this.state.loading = true;
        this.state.expandedId = null;
        try {
            const data = await this.orm.call(
                REPORT_MODEL,
                "get_general_ledger_data",
                [this.options]
            );
            this.state.accounts = data.accounts || [];
        } finally {
            this.state.loading = false;
        }
    }

    // Expand/collapse a line; lazily fetch its journal entry's Dr/Cr lines.
    async toggleExpand(line) {
        if (this.state.expandedId === line.id) {
            this.state.expandedId = null;
            return;
        }
        this.state.expandedId = line.id;
        const moveId = line.entry_id;
        if (moveId && !this.state.linesByMove[moveId]) {
            this.state.linesByMove[moveId] = await this.orm.searchRead(
                "account.move.line",
                [
                    ["move_id", "=", moveId],
                    ["display_type", "not in", ["line_section", "line_note"]],
                ],
                ENTRY_LINE_FIELDS
            );
        }
    }

    openEntry(line) {
        if (!line.entry_id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: line.entry_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    changeCriteria() {
        this.action.doAction(WIZARD_ACTION);
    }

    displayName(value) {
        // A searchRead Many2one value is [id, display_name] or false.
        return Array.isArray(value) ? value[1] : "";
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
}

GeneralLedger.template = "accounting_kmitl_reports.GeneralLedger";
GeneralLedger.props = ["*"];

registry.category("actions").add("kmitl_general_ledger", GeneralLedger);
