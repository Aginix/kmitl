/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart } from "@odoo/owl";
import { MultiRecordSelect } from "@accounting_kmitl_workflow/approval_queue/multi_record_select";

const DR_FIELDS = [
    "name",
    "date",
    "partner_id",
    "amount_net",
    "department_analytic_id",
    "fund_analytic_id",
    "source_analytic_id",
    "activity_analytic_id",
    "bill_count",
    "payment_status_display",
];

// Filter buckets backed by the MultiRecordSelect widget -> DR field.
const FILTER_FIELDS = {
    departments: "department_analytic_id",
    sources: "source_analytic_id",
    funds: "fund_analytic_id",
    activities: "activity_analytic_id",
};

/**
 * Generic disbursement approval queue, parametrised through the client
 * action context (``kind`` = ``audit`` | ``authorize``). Mirrors the
 * accounting_kmitl_workflow approval queue and reuses its MultiRecordSelect.
 */
export class DisbursementPaymentQueue extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.company = useService("company");
        const action = this.props.action || {};
        const ctx = action.context || action.params || {};
        const config = {
            audit: {
                state: "bills_posted",
                approve: "action_audit",
                batch: "action_audit_batch",
                title: _t("Audit Disbursements"),
                action: _t("Audit"),
                batchLabel: _t("Audit Selected"),
            },
            authorize: {
                state: "payment_audited",
                approve: "action_authorize",
                batch: "action_authorize_batch",
                title: _t("Authorize Disbursements"),
                action: _t("Authorize"),
                batchLabel: _t("Authorize Selected"),
            },
        }[ctx.kind || "audit"];
        this.queueState = config.state;
        this.approveMethod = config.approve;
        this.batchMethod = config.batch;
        this.fiscalYears = [];
        this.state = useState({
            loading: true,
            records: [],
            selectedIds: [],
            fiscalYearId: false,
            dateFrom: false,
            dateTo: false,
            departments: [],
            sources: [],
            funds: [],
            activities: [],
        });
        this.labels = {
            title: config.title,
            approveSelected: config.batchLabel,
            approve: config.action,
            empty: _t("No requests in this queue."),
            number: _t("Number"),
            date: _t("Date"),
            partner: _t("Partner"),
            amount: _t("Net Amount"),
            bills: _t("Bills"),
            payment: _t("Payment"),
            actions: _t("Actions"),
            open: _t("Open"),
            fiscalYear: _t("Fiscal Year"),
            dateFrom: _t("Date From"),
            dateTo: _t("Date To"),
            departments: _t("Departments"),
            sources: _t("Sources"),
            funds: _t("Funds"),
            activities: _t("Activities"),
        };
        onWillStart(async () => {
            this.companyId = this.company.currentCompany.id;
            this.fiscalYears = await this.orm.searchRead(
                "account.fiscal.year",
                [],
                ["id", "name", "date_from", "date_to"],
                { order: "date_from desc" }
            );
            await this.load();
        });
    }

    get domain() {
        const domain = [["state", "=", this.queueState]];
        if (this.state.dateFrom) {
            domain.push(["date", ">=", this.state.dateFrom]);
        }
        if (this.state.dateTo) {
            domain.push(["date", "<=", this.state.dateTo]);
        }
        for (const [key, field] of Object.entries(FILTER_FIELDS)) {
            const ids = this.state[key].map((record) => record.id);
            if (ids.length) {
                domain.push([field, "in", ids]);
            }
        }
        return domain;
    }

    async load() {
        this.state.loading = true;
        this.state.records = await this.orm.searchRead(
            "disbursement.request",
            this.domain,
            DR_FIELDS,
            { order: "date desc, id desc" }
        );
        const ids = this.state.records.map((record) => record.id);
        this.state.selectedIds = this.state.selectedIds.filter((id) =>
            ids.includes(id)
        );
        this.state.loading = false;
    }

    onFiscalYearChange(ev) {
        const id = parseInt(ev.target.value) || false;
        this.state.fiscalYearId = id;
        const fy = this.fiscalYears.find((f) => f.id === id);
        this.state.dateFrom = fy ? fy.date_from : false;
        this.state.dateTo = fy ? fy.date_to : false;
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

    onSelectionChange(key, selected) {
        if (Object.prototype.hasOwnProperty.call(FILTER_FIELDS, key)) {
            this.state[key] = selected;
            this.load();
        }
    }

    isFiscalYearSelected(fyId) {
        return fyId === this.state.fiscalYearId;
    }

    openRecord(record) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "disbursement.request",
            res_id: record.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async approve(record) {
        await this.orm.call("disbursement.request", this.approveMethod, [
            [record.id],
        ]);
        this.notification.add(_t("Done"), { type: "success" });
        await this.load();
    }

    async approveSelected() {
        if (!this.state.selectedIds.length) {
            return;
        }
        const action = await this.orm.call(
            "disbursement.request",
            this.batchMethod,
            [this.state.selectedIds]
        );
        if (action) {
            await this.action.doAction(action);
        }
        await this.load();
    }

    toggleSelect(recordId) {
        const selected = this.state.selectedIds;
        if (selected.includes(recordId)) {
            this.state.selectedIds = selected.filter((id) => id !== recordId);
        } else {
            this.state.selectedIds = [...selected, recordId];
        }
    }

    isSelected(recordId) {
        return this.state.selectedIds.includes(recordId);
    }

    toggleSelectAll() {
        this.state.selectedIds = this.allSelected
            ? []
            : this.state.records.map((record) => record.id);
    }

    get allSelected() {
        return (
            this.state.records.length > 0 &&
            this.state.selectedIds.length === this.state.records.length
        );
    }

    displayName(value) {
        return Array.isArray(value) ? value[1] : "";
    }

    formatCurrency(amount) {
        return (amount || 0).toLocaleString("th-TH", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
}

DisbursementPaymentQueue.template = "disbursement_finance_kmitl.PaymentQueue";
DisbursementPaymentQueue.components = { MultiRecordSelect };
DisbursementPaymentQueue.props = ["*"];

registry
    .category("actions")
    .add("disbursement_finance_kmitl.payment_queue", DisbursementPaymentQueue);
