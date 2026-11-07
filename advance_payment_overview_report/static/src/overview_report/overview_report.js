/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {Component, onWillStart, onWillUpdateProps, useState, useSubEnv} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";
import {WithSearch} from "@web/search/with_search/with_search";

const REPORT_MODEL = "advance.payment.overview.report";

// Badge colour per loan state / due status (Bootstrap 5.1 classes).
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
 * The report body: reads the native search model's domain and group-by and
 * renders the table under Odoo's own control panel.
 */
export class AdvancePaymentOverviewReport extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            columns: [],
            groups: [],
            totals: {},
            grouped: false,
            count: 0,
        });
        onWillStart(async () => {
            this.state.columns = await this.orm.call(REPORT_MODEL, "get_columns", []);
            await this.load(this.props);
        });
        onWillUpdateProps((nextProps) => this.load(nextProps));
    }

    options(props) {
        // The facets as the search bar shows them, for the printed header.
        const facets = this.env.searchModel.facets.map((facet) => {
            const values = facet.values.join(` ${facet.separator || "or"} `);
            const title = facet.type === "groupBy" ? "จัดกลุ่มตาม" : facet.title;
            return title ? `${title}: ${values}` : values;
        });
        return {
            domain: props.domain,
            group_by: props.groupBy,
            facets,
        };
    }

    async load(props) {
        this.state.loading = true;
        try {
            const data = await this.orm.call(REPORT_MODEL, "get_report_data", [
                this.options(props),
            ]);
            Object.assign(this.state, {
                groups: data.groups,
                totals: data.totals,
                grouped: data.grouped,
                count: data.count,
            });
        } finally {
            this.state.loading = false;
        }
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

    get labelSpan() {
        return this.state.columns.findIndex((column) => column[2]);
    }

    stateBadge(row) {
        return STATE_BADGES[row.state_code] || "bg-secondary";
    }

    dueBadge(row) {
        return DUE_BADGES[row.return_due_status_code] || "";
    }

    /** Opened in a new tab, so the report keeps its filters. */
    recordUrl(model, id) {
        return `/web#id=${id}&model=${model}&view_type=form`;
    }

    lines(value) {
        return value ? value.split("\n") : [];
    }

    async printReport() {
        const action = await this.orm.call(REPORT_MODEL, "action_print_pdf", [
            this.options(this.props),
        ]);
        await this.action.doAction(action);
    }

    async exportXlsx() {
        const action = await this.orm.call(REPORT_MODEL, "action_export_xlsx", [
            this.options(this.props),
        ]);
        await this.action.doAction(action);
    }
}

AdvancePaymentOverviewReport.template = "advance_payment_overview_report.OverviewReport";
AdvancePaymentOverviewReport.components = {ControlPanel};
AdvancePaymentOverviewReport.props = ["domain", "groupBy", "context?"];

/**
 * รายงานภาพรวมสัญญายืมเงิน — the client action: wraps the report in Odoo's
 * WithSearch so the search bar, filters, group-by and favourites are native.
 */
export class AdvancePaymentOverviewReportAction extends Component {
    setup() {
        // The ControlPanel reads this; only views get it from the action service.
        useSubEnv({config: {...this.env.config, viewSwitcherEntries: []}});
        this.orm = useService("orm");
        onWillStart(async () => {
            this.searchViewId = await this.orm.call(REPORT_MODEL, "get_search_view_id", []);
        });
    }

    get withSearchProps() {
        const {action} = this.props;
        return {
            resModel: "advance.payment",
            searchViewId: this.searchViewId,
            context: action.context || {},
            domain: action.domain || [],
            loadIrFilters: true,
            searchMenuTypes: ["filter", "groupBy", "favorite"],
        };
    }
}

AdvancePaymentOverviewReportAction.template =
    "advance_payment_overview_report.OverviewReportAction";
AdvancePaymentOverviewReportAction.components = {
    WithSearch,
    AdvancePaymentOverviewReport,
};
AdvancePaymentOverviewReportAction.props = ["*"];

registry
    .category("actions")
    .add("advance_payment_overview_report", AdvancePaymentOverviewReportAction);
