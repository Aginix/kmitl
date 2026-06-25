/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
import { MultiRecordSelect } from "../trial_balance/multi_record_select";
import { MoveLinesDetail } from "../common/move_lines_detail";

const REPORT_MODEL = "report.accounting_kmitl_reports.general_ledger_kmitl";
const WIZARD_ACTION = "accounting_kmitl_reports.action_general_ledger_wizard_kmitl";

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

export class GeneralLedger extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        this.fiscalYears = [];
        this.state = useState({
            loading: true,
            // Report data: the account sections returned by the compute.
            sections: [],
            // Row-based pagination across accounts (bounds the DOM on large
            // reports). pageSize counts data rows, not accounts.
            page: 0,
            pageSize: 100,
            // Expanded move-line rows (multiple may be open at once), by row id.
            expanded: {},
            // Lazily-fetched Dr/Cr breakdown of each journal entry, by move id.
            linesByMove: {},
            // Filters (mirror the Trial Balance).
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
            broughtForward: _t("Balance brought forward"),
            prevPage: _t("Previous page"),
            nextPage: _t("Next page"),
            rowsPerPage: _t("Rows per page"),
            // Filter placeholders (shared with the Trial Balance).
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
        const params = (this.props.action && this.props.action.params) || {};
        this.companyId = params.company_id || this.company.currentCompany.id;
        this.fiscalYears = await this.orm.searchRead(
            "account.fiscal.year",
            [],
            ["id", "name", "date_from", "date_to"],
            { order: "date_from desc" }
        );
        if (params.date_from && params.date_to) {
            // Seed from the wizard's criteria; the in-screen filters can refine.
            this.state.fiscalYearId = params.fiscal_year_id || false;
            this.state.dateFrom = params.date_from;
            this.state.dateTo = params.date_to;
            if (params.only_posted !== undefined) {
                this.state.onlyPosted = params.only_posted;
            }
            if (params.account_ids && params.account_ids.length) {
                const accs = await this.orm.read(
                    "account.account",
                    params.account_ids,
                    ["display_name"]
                );
                this.state.accounts = accs.map((a) => ({
                    id: a.id,
                    name: a.display_name,
                }));
                // Specific accounts were picked: show them even at a zero balance.
                this.state.hideAt0 = false;
            }
        } else {
            // Opened directly (no wizard): default to the current fiscal year.
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
        };
    }

    async load() {
        if (!this.state.dateFrom || !this.state.dateTo) {
            return;
        }
        this.state.loading = true;
        this.state.expanded = {};
        this.state.page = 0;
        try {
            const data = await this.orm.call(
                REPORT_MODEL,
                "get_general_ledger_data",
                [this.options]
            );
            this.state.sections = data.accounts || [];
        } finally {
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------
    // Pagination (row-based, spanning accounts)
    // ------------------------------------------------------------------
    get _accountSpans() {
        // Each account occupies max(1, lineCount) units, so an account with no
        // lines (opening balance only) still gets a page slot.
        let cursor = 0;
        return this.state.sections.map((acc) => {
            const span = Math.max(1, acc.lines.length);
            const start = cursor;
            cursor += span;
            return { acc, start, span, n: acc.lines.length };
        });
    }

    get totalUnits() {
        return this._accountSpans.reduce((sum, a) => sum + a.span, 0);
    }

    get pageCount() {
        return Math.max(1, Math.ceil(this.totalUnits / this.state.pageSize));
    }

    get showPager() {
        return this.pageCount > 1;
    }

    get isFirstPage() {
        return this.state.page <= 0;
    }

    get isLastPage() {
        return this.state.page + 1 >= this.pageCount;
    }

    // Accounts sliced to the current page window, with flags driving the
    // opening / brought-forward / carried-forward rows at page boundaries.
    get pagedSections() {
        const start = this.state.page * this.state.pageSize;
        const end = start + this.state.pageSize;
        const out = [];
        for (const { acc, start: accStart, span, n } of this._accountSpans) {
            if (accStart + span <= start || accStart >= end) {
                continue;
            }
            if (n === 0) {
                out.push({
                    ...acc,
                    lines: [],
                    showOpening: true,
                    broughtForward: null,
                    showCarried: true,
                });
                continue;
            }
            const from = Math.max(0, start - accStart);
            const to = Math.min(n, end - accStart);
            out.push({
                ...acc,
                lines: acc.lines.slice(from, to),
                showOpening: from === 0,
                broughtForward: from === 0 ? null : acc.lines[from - 1].balance,
                showCarried: to === n,
            });
        }
        return out;
    }

    prevPage() {
        if (!this.isFirstPage) {
            this.state.page -= 1;
        }
    }

    nextPage() {
        if (!this.isLastPage) {
            this.state.page += 1;
        }
    }

    setPageSize(ev) {
        this.state.pageSize = parseInt(ev.target.value) || 100;
        this.state.page = 0;
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

    // ------------------------------------------------------------------
    // Row interactions
    // ------------------------------------------------------------------
    // Expand/collapse a line; lazily fetch its journal entry's Dr/Cr lines.
    // Multiple rows can stay open at the same time.
    async toggleExpand(line) {
        if (this.state.expanded[line.id]) {
            delete this.state.expanded[line.id];
            return;
        }
        this.state.expanded[line.id] = true;
        const moveId = line.entry_id;
        if (moveId && !this.state.linesByMove[moveId]) {
            this.state.linesByMove[moveId] = await this.orm.call(
                REPORT_MODEL,
                "get_move_lines_detail",
                [moveId]
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

    // Reopen the entry-point wizard to pick fresh criteria.
    changeCriteria() {
        this.action.doAction(WIZARD_ACTION);
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

    // Like format() but renders an exact zero as "0.00" (carried-forward totals).
    formatTotal(value) {
        return (value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    // Muted-red class for negative balances (the minus sign carries meaning;
    // colour is only a secondary cue).
    negClass(value) {
        return value < 0 ? "o_kmitl_gl_neg" : "";
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
GeneralLedger.components = { MultiRecordSelect, MoveLinesDetail };
GeneralLedger.props = ["*"];

registry.category("actions").add("kmitl_general_ledger", GeneralLedger);
