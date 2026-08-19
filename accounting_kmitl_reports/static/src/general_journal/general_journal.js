/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
import { MultiRecordSelect } from "../trial_balance/multi_record_select";
import { MoveLinesDetail } from "../common/move_lines_detail";

const REPORT_MODEL = "report.accounting_kmitl_reports.general_journal_kmitl";

// Selected-record state buckets that feed the report options.
const SELECTION_KEYS = [
    "journals",
    "partners",
    "departments",
    "sources",
    "funds",
    "activities",
];

export class GeneralJournal extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        this.fiscalYears = [];
        this.state = useState({
            loading: true,
            // Report data: the journal entries returned by the compute.
            entries: [],
            // Expanded entry rows (multiple may be open at once), by entry id.
            expanded: {},
            // Lazily-fetched detail lines of each entry, by move id.
            linesByMove: {},
            // "Expand all" toggle: expand every entry on the current page.
            expandAll: false,
            // Row-based pagination (rows = entries).
            page: 0,
            pageSize: 50,
            // Filters.
            fiscalYearId: false,
            dateFrom: false,
            dateTo: false,
            onlyPosted: true,
            showAdvanced: false,
            // selections (each an Array<{id, name}>)
            journals: [],
            partners: [],
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
        });
        this.labels = {
            title: _t("General Journal"),
            printPdf: _t("Print PDF"),
            exportExcel: _t("Export Excel"),
            exportCsv: _t("Export CSV"),
            empty: _t("No entries for the selected criteria."),
            datetime: _t("Date-Time"),
            number: _t("Number"),
            journal: _t("Journal"),
            reference: _t("Reference"),
            account: _t("Account"),
            label: _t("Label"),
            partner: _t("Partner"),
            debit: _t("Debit"),
            credit: _t("Credit"),
            narration: _t("Narration"),
            maker: _t("Maker"),
            open: _t("Open"),
            prevPage: _t("Previous page"),
            nextPage: _t("Next page"),
            rowsPerPage: _t("Rows per page"),
            // Filter placeholders (shared with the other reports).
            journals: _t("Journals"),
            partners: _t("Partners"),
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
            journal_ids: this.state.journals.map((r) => r.id),
            partner_ids: this.state.partners.map((r) => r.id),
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
        this.state.expanded = {};
        this.state.page = 0;
        try {
            const data = await this.orm.call(
                REPORT_MODEL,
                "get_general_journal_data",
                [this.options]
            );
            this.state.entries = data.entries || [];
        } finally {
            this.state.loading = false;
        }
        if (this.state.expandAll) {
            await this.expandCurrentPage();
        }
    }

    // ------------------------------------------------------------------
    // Pagination (rows = entries)
    // ------------------------------------------------------------------
    get pageCount() {
        return Math.max(1, Math.ceil(this.state.entries.length / this.state.pageSize));
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

    get pagedEntries() {
        const start = this.state.page * this.state.pageSize;
        return this.state.entries.slice(start, start + this.state.pageSize);
    }

    prevPage() {
        if (!this.isFirstPage) {
            this.state.page -= 1;
            if (this.state.expandAll) {
                this.expandCurrentPage();
            }
        }
    }

    nextPage() {
        if (!this.isLastPage) {
            this.state.page += 1;
            if (this.state.expandAll) {
                this.expandCurrentPage();
            }
        }
    }

    setPageSize(ev) {
        this.state.pageSize = parseInt(ev.target.value) || 50;
        this.state.page = 0;
        if (this.state.expandAll) {
            this.expandCurrentPage();
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
    // Row interactions
    // ------------------------------------------------------------------
    // Expand/collapse an entry; lazily fetch its detail lines. Multiple entries
    // can stay open at the same time.
    async toggleExpand(entry) {
        if (this.state.expanded[entry.id]) {
            delete this.state.expanded[entry.id];
            return;
        }
        this.state.expanded[entry.id] = true;
        if (!this.state.linesByMove[entry.id]) {
            this.state.linesByMove[entry.id] = await this.orm.call(
                REPORT_MODEL,
                "get_move_lines_detail",
                [entry.id]
            );
        }
    }

    // Expand every entry on the current page, batch-fetching the detail lines
    // that are not cached yet (one round-trip per page).
    async expandCurrentPage() {
        const moveIds = new Set();
        for (const entry of this.pagedEntries) {
            this.state.expanded[entry.id] = true;
            if (!this.state.linesByMove[entry.id]) {
                moveIds.add(entry.id);
            }
        }
        if (moveIds.size) {
            const data = await this.orm.call(
                REPORT_MODEL,
                "get_move_lines_details",
                [[...moveIds]]
            );
            Object.assign(this.state.linesByMove, data);
        }
    }

    async onToggleExpandAll(ev) {
        this.state.expandAll = ev.target.checked;
        if (this.state.expandAll) {
            await this.expandCurrentPage();
        } else {
            this.state.expanded = {};
        }
    }

    openEntry(entry) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: entry.id,
            views: [[false, "form"]],
            target: "current",
        });
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

GeneralJournal.template = "accounting_kmitl_reports.GeneralJournal";
GeneralJournal.components = { MultiRecordSelect, MoveLinesDetail };
GeneralJournal.props = ["*"];

registry.category("actions").add("kmitl_general_journal", GeneralJournal);
